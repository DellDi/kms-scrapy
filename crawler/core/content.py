from typing import Dict, Any, List
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from docx import Document
from pptx import Presentation
import pylibmagic
import magic
import os
import requests
from pydantic import BaseModel, Field

class KMSItem(BaseModel):
    """KMS文档项目模型"""
    title: str = Field(description="文档标题")
    content: str = Field(description="文档内容")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件信息")

class ContentParser:
    """内容解析器，处理页面内容和附件"""

    @staticmethod
    def parse_page_content(html_content: str) -> tuple[str, str]:
        """解析页面内容，返回标题和正文"""
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.select_one('#title-text').get_text(strip=True)
        content = soup.select_one('#main-content').get_text()
        return title, content

    @staticmethod
    def process_image(image_path: str) -> str:
        """处理图片文件，提取文本"""
        image = Image.open(image_path)
        return pytesseract.image_to_string(image, lang='chi_sim')

    @staticmethod
    def process_pdf(pdf_path: str) -> str:
        """处理PDF文件，提取文本"""
        pages = convert_from_path(pdf_path)
        text = ''
        for page in pages:
            text += pytesseract.image_to_string(page, lang='chi_sim')
        return text

    @staticmethod
    def process_word(docx_path: str) -> str:
        """处理Word文件，提取文本"""
        doc = Document(docx_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])

    @staticmethod
    def process_ppt(pptx_path: str) -> str:
        """处理PPT文件，提取文本"""
        prs = Presentation(pptx_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, 'text'):
                    text.append(shape.text)
        return '\n'.join(text)

    @staticmethod
    def process_attachment(file_url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """处理附件，返回附件信息"""
        file_response = requests.get(file_url, headers=headers)
        if file_response.status_code != 200:
            return None

        file_type = magic.from_buffer(file_response.content, mime=True)
        temp_path = f'temp_{os.path.basename(file_url)}'

        try:
            with open(temp_path, 'wb') as f:
                f.write(file_response.content)

            text = None
            if 'image' in file_type:
                text = ContentParser.process_image(temp_path)
            elif 'pdf' in file_type:
                text = ContentParser.process_pdf(temp_path)
            elif 'word' in file_type:
                text = ContentParser.process_word(temp_path)
            elif 'powerpoint' in file_type:
                text = ContentParser.process_ppt(temp_path)

            if text:
                return {
                    'url': file_url,
                    'type': file_type,
                    'content': text
                }
            return None

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)