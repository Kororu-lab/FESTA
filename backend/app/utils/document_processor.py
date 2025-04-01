import os
from pathlib import Path
from typing import Optional, Dict, Any
import PyPDF2
import markdown
from bs4 import BeautifulSoup
import re
import shutil
from datetime import datetime

class DocumentProcessor:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.papers_dir = self.base_dir / "data" / "papers"
        self.processed_dir = self.base_dir / "data" / "processed"
        self.db_dir = self.base_dir / "data" / "db"
        
        # 디렉토리 생성
        for dir_path in [self.papers_dir, self.processed_dir, self.db_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def save_document(self, file_content: bytes, original_filename: str) -> Dict[str, Any]:
        """문서를 저장하고 메타데이터를 반환합니다."""
        # 파일 확장자 추출
        file_ext = Path(original_filename).suffix.lower()
        
        # 허용된 파일 형식 확인
        allowed_extensions = {'.pdf', '.md', '.html', '.tex', '.txt'}
        if file_ext not in allowed_extensions:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {file_ext}")
        
        # 고유한 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{original_filename}"
        file_path = self.papers_dir / unique_filename
        
        # 파일 저장
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # 메타데이터 생성
        metadata = {
            "original_filename": original_filename,
            "saved_filename": unique_filename,
            "file_path": str(file_path),
            "file_type": file_ext[1:],  # 확장자에서 점 제거
            "upload_date": timestamp,
            "file_size": len(file_content)
        }
        
        return metadata

    def extract_text(self, file_path: Path) -> str:
        """문서에서 텍스트를 추출합니다."""
        file_ext = file_path.suffix.lower()
        
        if file_ext == '.pdf':
            return self._extract_pdf_text(file_path)
        elif file_ext == '.md':
            return self._extract_markdown_text(file_path)
        elif file_ext == '.html':
            return self._extract_html_text(file_path)
        elif file_ext == '.tex':
            return self._extract_latex_text(file_path)
        elif file_ext == '.txt':
            return self._extract_txt_text(file_path)
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {file_ext}")

    def _extract_pdf_text(self, file_path: Path) -> str:
        """PDF 파일에서 텍스트를 추출합니다."""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _extract_markdown_text(self, file_path: Path) -> str:
        """Markdown 파일에서 텍스트를 추출합니다."""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # HTML로 변환
            html = markdown.markdown(content)
            # HTML에서 텍스트 추출
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()

    def _extract_html_text(self, file_path: Path) -> str:
        """HTML 파일에서 텍스트를 추출합니다."""
        with open(file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            return soup.get_text()

    def _extract_latex_text(self, file_path: Path) -> str:
        """LaTeX 파일에서 텍스트를 추출합니다."""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # LaTeX 주석 제거
            content = re.sub(r'%.*$', '', content, flags=re.MULTILINE)
            # LaTeX 명령어 제거
            content = re.sub(r'\\[a-zA-Z]+{([^}]*)}', r'\1', content)
            return content

    def _extract_txt_text(self, file_path: Path) -> str:
        """텍스트 파일에서 텍스트를 추출합니다."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def process_document(self, file_path: Path) -> Dict[str, Any]:
        """문서를 처리하고 결과를 반환합니다."""
        # 텍스트 추출
        text = self.extract_text(file_path)
        
        # 처리된 파일 저장
        processed_filename = f"processed_{file_path.name}.txt"
        processed_path = self.processed_dir / processed_filename
        
        with open(processed_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return {
            "original_file": str(file_path),
            "processed_file": str(processed_path),
            "text_length": len(text),
            "processed_date": datetime.now().strftime("%Y%m%d_%H%M%S")
        } 