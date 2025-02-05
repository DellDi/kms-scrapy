import os
import mimetypes
import urllib.parse
from typing import Dict, Any, List, Optional

from bs4 import BeautifulSoup
from PIL import Image
from docx import Document
from pptx import Presentation
import pytesseract
from pdf2image import convert_from_path
import pylibmagic
import magic
import requests
from pydantic import BaseModel, Field

class KMSItem(BaseModel):
    """KMS文档项目"""
    title: str
    content: str
    attachments: Optional[List[dict]] = []

    model_config = {
        'arbitrary_types_allowed': True,
        'json_schema_extra': {
            'examples': [{
                'title': '示例文档',
                'content': '文档内容',
                'attachments': []
            }]
        }
    }

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
        try:
            image = Image.open(image_path)
            return pytesseract.image_to_string(image, lang='chi_sim')
        except pytesseract.TesseractNotFoundError:
            import logging
            logging.error('Tesseract OCR未安装或未添加到PATH中。请参考README文件安装必要的系统依赖。')
            return None
        except Exception as e:
            import logging
            logging.warning(f'图片文本提取失败: {str(e)}')
            return None

    @staticmethod
    def process_pdf(pdf_path: str) -> str:
        """处理PDF文件，提取文本"""
        try:
            pages = convert_from_path(pdf_path)
            text = ''
            for page in pages:
                text += pytesseract.image_to_string(page, lang='chi_sim')
            return text
        except (pytesseract.TesseractNotFoundError, Exception) as e:
            import logging
            logging.warning(f'PDF文本提取失败: {str(e)}')
            return None

    @staticmethod
    def process_word(docx_path: str) -> str:
        """处理Word文件，提取文本"""
        try:
            doc = Document(docx_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            import logging
            logging.warning(f'Word文本提取失败: {str(e)}')
            return None

    @staticmethod
    def process_ppt(pptx_path: str) -> str:
        """处理PPT文件，提取文本"""
        try:
            prs = Presentation(pptx_path)
            text = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, 'text'):
                        text.append(shape.text)
            return '\n'.join(text)
        except Exception as e:
            import logging
            logging.warning(f'PPT文本提取失败: {str(e)}')
            return None

    @staticmethod
    def process_attachment(file_url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """处理附件，返回附件信息"""
        file_response = requests.get(file_url, headers=headers)
        if file_response.status_code != 200:
            return None

        file_type = magic.from_buffer(file_response.content, mime=True)
        # 从URL中获取原始文件名，并去除URL参数
        # 从URL中获取原始文件名，进行URL解码并去除URL参数
        file_name = os.path.basename(file_url).split('?')[0]
        file_name = urllib.parse.unquote(file_name)

        # 如果URL中没有文件后缀，尝试从Content-Type获取
        if '.' not in file_name:
            content_type = file_response.headers.get('Content-Type', '')
            ext = mimetypes.guess_extension(content_type)
            if ext:
                file_name = f'{file_name}{ext}'

        temp_path = f'temp_{file_name}'

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

            return {
                'url': file_url,
                'type': file_type,
                'filename': file_name,
                'content': file_response.content,
                'extracted_text': text
            }

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)