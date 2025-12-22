import time
from datetime import datetime
import logging
import json
import math
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.config import GlobalConfig
from src.drivers.arxiv import ArxivDriver
from src.drivers.llm import DeepSeekDriver
from src.drivers.email import EmailDriver
from src.drivers.pdf import PDFDriver
from src.utils.file_utils import sanitize_filename, ensure_dir
from src.utils.text_utils import normalize_list

logger = logging.getLogger("service.daily")

class DailyFlow:
    def __init__(self):
        self.config = GlobalConfig
        self.arxiv = ArxivDriver()
        self.llm = DeepSeekDriver()
        self.email = EmailDriver()
        self.pdf = PDFDriver()
        
        # 路径定义
        self.assets_dir = self.config.assets_path
        self.inbox_dir = self.config.data_path / "inbox"
        self.reports_dir = self.config.data_path / "reports" / "daily_meta"
        self.cache_dir = self.config.data_path / "raw_cache"
        
        now = datetime.now()
        self.reports_dir = self.config.data_path / "reports" / "daily" / f"{now.year}" / f"{now.month:02d}"
        
        # 确保目录存在
        ensure_dir(self.reports_dir)
        ensure_dir(self.inbox_dir)
        ensure_dir(self.cache_dir)

        # 模板引擎
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.assets_dir)),
            autoescape=False
        )

    def _render(self, template_name: str, context: dict) -> str:
        """统一渲染函数"""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"❌ Template error ({template_name}): {e}")
            return ""

    def _save_checkpoint(self, papers: List[Dict], date_str: str):
        ckpt_path = self.cache_dir / f"checkpoint_{date_str}.json"
        with open(ckpt_path, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)

    def _process_single_batch(self, batch: List[Dict], batch_idx: int, total_batches: int, system_prompt: str) -> List[Dict]:
        """
        [原子操作] 处理单个批次。
        这个函数将在独立的线程中运行。
        """
        # 这里的 logger 在多线程下是安全的，但顺序可能会乱，这没关系
        logger.info(f"⚡ Batch {batch_idx}/{total_batches} -> Processing ({len(batch)} papers)...")
        
        user_content = "Please analyze these papers:\n\n"
        # 建立局部索引映射 (ID: 0~batch_size)
        for j, p in enumerate(batch):
            user_content += f"ID: {j} | Title: {p['title']}\nAbstract: {p['summary']}\n---\n"
        
        processed_batch = []
        try:
            # 调用 LLM (耗时操作)
            raw_json = self.llm.chat_json(system_prompt, user_content)
            result_list = normalize_list(raw_json)
            
            # 建立结果映射表
            review_map = {}
            for r in result_list:
                raw_id = r.get('id')
                try:
                    if raw_id is not None:
                        review_map[int(raw_id)] = r
                except ValueError:
                    continue
            
            # 合并结果
            for local_id, p in enumerate(batch):
                review = review_map.get(local_id)
                if review:
                    try:
                        p['score'] = float(review.get('score', 0))
                    except ValueError:
                        p['score'] = 0.0
                        
                    p['reason'] = review.get('reason', 'N/A')
                    p['summary_zh'] = review.get('summary_zh', 'N/A')
                    
                    if p['score'] >= 4.0:
                        logger.info(f"   🌟 HIT [{p['score']}] (Batch {batch_idx}): {p['title'][:50]}...")
                else:
                    p['score'] = 0.0
                    p['reason'] = "LLM missed this paper"
                
                processed_batch.append(p)

            logger.info(f"✅ Batch {batch_idx}/{total_batches} -> Done.")
            return processed_batch

        except Exception as e:
            logger.error(f"❌ Batch {batch_idx} failed: {e}")
            # 容错处理：如果该批次失败，返回原数据并标记 0 分，防止整个流程崩溃
            for p in batch:
                p['score'] = 0.0
                p['reason'] = f"Batch Error: {str(e)}"
                processed_batch.append(p)
            return processed_batch

    def _batch_score_papers(self, papers: List[Dict], batch_size=25) -> List[Dict]:
        """
        [主控逻辑] 多线程调度器
        """
        context = {
            "user_profile": self.config.get('daily_news.user_profile', ""),
            "black_list": self.config.get('daily_news.black_list', []),
            "grey_list": self.config.get('daily_news.grey_list', []),
            "white_list": self.config.get('daily_news.white_list', [])
        }
        system_prompt = self._render("prompts/daily_score.md.j2", context)

        total_papers = len(papers)
        # 向上取整计算批次
        num_batches = math.ceil(total_papers / batch_size)
        
        # 获取并发数配置，默认为 5
        max_workers = self.config.get('system.max_workers', 5)
        
        logger.info(f"🧠 Scoring Start: {total_papers} papers in {num_batches} batches.")
        logger.info(f"🚀 Thread Pool: {max_workers} workers active.")

        all_results = []
        
        # 准备数据切片
        chunks = []
        for i in range(0, total_papers, batch_size):
            chunks.append(papers[i : i + batch_size])

        # 启动线程池
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            # future_to_batch 是一个字典，用来追踪每个任务对应的批次ID
            future_to_batch = {
                executor.submit(
                    self._process_single_batch, 
                    chunk, 
                    idx + 1, 
                    num_batches, 
                    system_prompt
                ): idx + 1 
                for idx, chunk in enumerate(chunks)
            }

            # 收集结果 (as_completed 会在某个任务完成时立即 yield)
            for future in as_completed(future_to_batch):
                batch_id = future_to_batch[future]
                try:
                    result_chunk = future.result()
                    all_results.extend(result_chunk)
                except Exception as exc:
                    logger.critical(f"🔥 Worker thread {batch_id} crashed unrecoverably: {exc}")
        
        return all_results

    def _download_high_scores(self, papers: List[Dict], threshold=4.0):
        targets = [p for p in papers if p.get('score', 0) >= threshold]
        
        if not targets:
            logger.info("😴 No high-scoring papers to download.")
            return

        logger.info(f"📥 Downloading {len(targets)} high-score papers...")
        
        success_count = 0
        for i, p in enumerate(targets):
            arxiv_id = p['arxiv_url'].split('/')[-1]
            safe_title = sanitize_filename(p['title'])
            filename = f"[{arxiv_id}] {safe_title}.pdf"
            save_path = self.inbox_dir / filename
            
            prefix = f"[{i+1}/{len(targets)}]"
            
            try:
                if save_path.exists():
                     logger.info(f"   ⏭️ {prefix} Skipped (Exists): {filename[:50]}...")
                     p['local_path'] = str(save_path)
                     success_count += 1
                     continue

                logger.info(f"   ⬇️ {prefix} Downloading: {filename[:50]}...")
                final_path = self.pdf.download(p['pdf_url'], save_path)
                
                if final_path:
                    p['local_path'] = str(final_path)
                    success_count += 1
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"   ❌ {prefix} Failed: {e}")

        logger.info(f"✅ Download Summary: {success_count}/{len(targets)} success.")

    def run(self, days_back=1, force_email=False, max_limit=None):
        logger.info(f"🚀 === Daily Flow Started (Days: {days_back}) ===")
        
        # 1. Fetch
        subjects = self.config.get('daily_news.subjects', ['cs.CR'])
        query = " OR ".join([f"cat:{s}" for s in subjects])
        
        try:
            papers = self.arxiv.search(query=query, days_back=days_back, limit=max_limit)
        except Exception as e:
            logger.error(f"🛑 Fetch failed: {e}")
            return

        if not papers:
            logger.info("📭 No new papers found today.")
            return
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        self._save_checkpoint(papers, date_str)

        # 防止后面 LLM 崩溃导致数据丢失，不需要重新爬 Arxiv
        self._save_checkpoint(papers, time.strftime("%Y-%m-%d"))
        # logger.info(f"💾 Checkpoint saved: {len(papers)} papers cached.")

        if max_limit:
             papers = papers[:max_limit]
             logger.warning(f"✂️ DEV MODE: Limiting to {max_limit} papers.")

        # 2. Score
        logger.info("--- 🧠 Stage 2: Semantic Scoring ---")
        scored_papers = self._batch_score_papers(papers, batch_size=30)

        # 3. Download
        logger.info("--- 📥 Stage 3: Asset Acquisition ---")
        self._download_high_scores(scored_papers, threshold=4.0)

        # 4. Report
        scored_papers.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Save Metadata
        date_str = time.strftime("%Y-%m-%d")
        meta_file = self.reports_dir / f"{date_str}_daily.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(scored_papers, f, ensure_ascii=False, indent=2)
        # logger.info(f"💾 Metadata saved to: {meta_file.name}")

        # Email
        high_quality_papers = [p for p in scored_papers if p.get('score', 0) >= 3.5]
        if high_quality_papers or force_email:
            logger.info(f"--- 📧 Stage 4: Reporting ({len(high_quality_papers)} candidates) ---")
            self._send_daily_report(scored_papers, date_str)
        else:
            logger.info("--- 📧 Stage 4: Skipped (No high scores) ---")

        logger.info("🎉 === Daily Flow Complete ===")

    def _send_daily_report(self, all_papers: List[Dict], date_str: str):
        send_threshold = self.config.get('email.send_threshold', 2.0)
        top_k = self.config.get('email.top_k', 15)
        
        display_papers = all_papers[:top_k]
        hidden_count = len(all_papers) - len(display_papers)
        
        # 渲染邮件模板
        # 注意：templates/email_daily.html 的路径是相对于 assets 的
        html = self._render("templates/email_daily.html", {
            "date_str": date_str,
            "total_count": len(all_papers),
            "display_papers": display_papers,
            "hidden_count": hidden_count
        })
        qualified_count = len([p for p in all_papers if p.get('score', 0) >= send_threshold])
        subject = f"ScholarCore Daily: {qualified_count} Papers Selected ({date_str})"
        
        self.email.send(subject, html)