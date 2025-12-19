import os
import requests
import fitz  # PyMuPDF
import logging
from pathlib import Path
from typing import Optional

from src.core.exceptions import FetchError, ProcessingError, FileWriteError

logger = logging.getLogger("driver.pdf")

class PDFDriver:
    def __init__(self):
        # 伪装成浏览器，防止 403 Forbidden
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def download(self, url: str, save_path: Path) -> Path:
        """
        原子化下载：先下载到 .tmp，成功后再重命名。
        """
        if save_path.exists():
            # 这里可以加一个校验：如果文件大小为0，视为损坏，强制重新下载
            if save_path.stat().st_size > 0:
                logger.info(f"PDF exists, skipping: {save_path.name}")
                return save_path
            else:
                logger.warning(f"Found empty PDF file, re-downloading: {save_path.name}")
                
        logger.info(f"Downloading PDF: {url} -> {save_path}")
        
        # 临时文件路径
        temp_path = save_path.with_suffix('.tmp')
        
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=30)
            if response.status_code != 200:
                raise FetchError("Download failed", resource_url=url, status_code=response.status_code)
            
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入临时文件
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 原子操作：重命名
            # 如果 temp_path 写完了没报错，说明文件是完整的，这就替换过去
            if temp_path.exists():
                shutil.move(str(temp_path), str(save_path))
            
            return save_path
        
        except Exception as e:
            # 清理垃圾
            if temp_path.exists():
                os.remove(temp_path)
            
            if isinstance(e, requests.RequestException):
                raise FetchError(f"Network error: {str(e)}", resource_url=url)
            raise FileWriteError(f"Write error: {str(e)}", file_path=str(save_path))

    def parse_text(self, pdf_path: Path) -> str:
        """
        解析 PDF，提取文本并保留图片占位符。
        """
        if not pdf_path.exists():
            raise ProcessingError("PDF file not found", details={"path": str(pdf_path)})

        logger.info(f"Parsing PDF: {pdf_path.name}")
        full_text = ""
        
        try:
            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc):
                    # 1. 提取纯文本
                    text = page.get_text()
                    
                    # 2. 检测图片 (Good Taste: 告诉 AI 这里有图，也许很重要)
                    image_list = page.get_images(full=True)
                    images_info = ""
                    if image_list:
                        images_info = f"\n\n[Page {page_num + 1} contains {len(image_list)} images/diagrams]\n\n"
                    
                    # 3. 拼接
                    full_text += f"--- Page {page_num + 1} ---\n{text}{images_info}\n"
            
            return full_text

        except Exception as e:
            raise ProcessingError(
                message="Failed to parse PDF content", 
                processor_name="PyMuPDF",
                details={"file": str(pdf_path), "error": str(e)}
            )