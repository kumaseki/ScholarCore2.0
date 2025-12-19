# src/drivers/arxiv.py
import arxiv
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.config import GlobalConfig
from src.core.exceptions import FetchError

logger = logging.getLogger("driver.arxiv")

class ArxivDriver:
    def __init__(self):
        self.config = GlobalConfig
        self.safety_limit = 3000
        self.client_settings = {
            "page_size": 100,
            "delay_seconds": 3.0,
            "num_retries": 5
        }

    @retry(
        retry=retry_if_exception_type(Exception), # 捕获所有异常进行重试
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _fetch_from_client(self, search_obj):
        """
        受保护的原子操作：连接 Arxiv 并获取生成器。
        注意：Arxiv 是 Lazy Load，这里只是建立了连接意图，真正的网络请求发生在迭代时。
        为了确保 Retry 生效，我们在这里强制转换成 list (虽然这会消耗内存，但对于 daily 任务是安全的)。
        """
        logger.debug(f"🔌 Connecting to Arxiv API...")
        client = arxiv.Client(**self.client_settings)
        # 强制消耗生成器，触发网络请求，以便 catch 异常
        return list(client.results(search_obj))

    def search(self, query: str, days_back: int = 1, limit: int = None) -> List[Dict[str, Any]]:
        logger.info(f"🔍 Searching Arxiv: query='{query}', days_back={days_back}, limit={limit}")
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        # 核心逻辑：如果有 limit，就用 limit；否则用 safety_limit
        # 这能防止测试时下载几千篇
        actual_max = limit if limit else self.safety_limit

        search_obj = arxiv.Search(
            query=query,
            max_results=actual_max, # <--- 这里生效！
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        try:
            # 调用受保护的方法
            all_results = self._fetch_from_client(search_obj)
            
            clean_results = []
            for result in all_results:
                # 时间熔断
                if result.published < cutoff_date:
                    logger.info(f"🛑 Reached cutoff date ({result.published.date()}), stopping.")
                    break
                
                paper_meta = {
                    "title": result.title.replace("\n", " ").strip(),
                    "authors": [a.name for a in result.authors],
                    "summary": result.summary.replace("\n", " ").strip(),
                    "published_date": result.published.isoformat(),
                    "arxiv_url": result.entry_id,
                    "pdf_url": result.pdf_url,
                    "categories": result.categories,
                    "journal_ref": result.journal_ref or "N/A"
                }
                clean_results.append(paper_meta)

            logger.info(f"✅ Fetched {len(clean_results)} papers from Arxiv.")
            return clean_results

        except Exception as e:
            logger.error(f"🔥 Arxiv Search Failed after retries: {e}")
            raise FetchError(
                message="Arxiv API unavailable",
                resource_url="arxiv_api",
                details={"query": query, "error": str(e)}
            )