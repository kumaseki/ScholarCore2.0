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
        下载 PDF 到指定路径。
        """
        if save_path.exists():
            logger.info(f"PDF already exists, skipping download: {save_path.name}")
            return save_path

        logger.info(f"Downloading PDF: {url} -> {save_path}")
        
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=30)
            if response.status_code != 200:
                raise FetchError(
                    message="Download failed", 
                    resource_url=url, 
                    status_code=response.status_code
                )
            
            # 确保父目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return save_path

        except requests.RequestException as e:
            raise FetchError(f"Network error during download: {str(e)}", resource_url=url)
        except IOError as e:
            raise FileWriteError(f"Failed to write PDF file: {str(e)}", file_path=str(save_path))

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