import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """데이터베이스와 테이블을 초기화합니다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # documents 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    saved_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    upload_date TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    processed_file TEXT,
                    text_length INTEGER,
                    processed_date TEXT,
                    title TEXT,
                    authors TEXT,
                    abstract TEXT,
                    keywords TEXT,
                    publication_date TEXT,
                    journal TEXT,
                    doi TEXT,
                    citations TEXT,
                    categories TEXT,
                    tags TEXT,
                    vector_id TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            ''')
            
            conn.commit()

    def insert_document(self, document: Dict[str, Any]) -> str:
        """문서를 데이터베이스에 삽입합니다."""
        # 리스트 타입의 필드를 JSON 문자열로 변환
        for field in ['authors', 'keywords', 'citations', 'references', 'categories', 'tags']:
            if field in document and document[field]:
                document[field] = json.dumps(document[field])

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ID 생성 (timestamp + random string)
            doc_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{document['saved_filename']}"
            
            # SQL 쿼리 생성
            fields = list(document.keys())
            placeholders = ','.join(['?' for _ in fields])
            fields_str = ','.join(fields)
            
            query = f'''
                INSERT INTO documents (id, {fields_str})
                VALUES (?, {placeholders})
            '''
            
            # 값 준비
            values = [doc_id] + [document[field] for field in fields]
            
            cursor.execute(query, values)
            conn.commit()
            
            return doc_id

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """문서를 ID로 조회합니다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 컬럼 이름 가져오기
            columns = [description[0] for description in cursor.description]
            
            # 결과를 딕셔너리로 변환
            result = dict(zip(columns, row))
            
            # JSON 문자열을 리스트로 변환
            for field in ['authors', 'keywords', 'citations', 'references', 'categories', 'tags']:
                if field in result and result[field]:
                    result[field] = json.loads(result[field])
            
            return result

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """문서를 업데이트합니다."""
        # 리스트 타입의 필드를 JSON 문자열로 변환
        for field in ['authors', 'keywords', 'citations', 'references', 'categories', 'tags']:
            if field in updates and updates[field]:
                updates[field] = json.dumps(updates[field])

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 업데이트 쿼리 생성
            set_clause = ','.join([f"{field} = ?" for field in updates.keys()])
            query = f'''
                UPDATE documents 
                SET {set_clause}, updated_at = ?
                WHERE id = ?
            '''
            
            # 값 준비
            values = list(updates.values()) + [datetime.now(), doc_id]
            
            cursor.execute(query, values)
            conn.commit()
            
            return cursor.rowcount > 0

    def delete_document(self, doc_id: str) -> bool:
        """문서를 삭제합니다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            conn.commit()
            return cursor.rowcount > 0

    def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """문서를 검색합니다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 제목, 저자, 초록, 키워드에서 검색
            search_query = f'''
                SELECT * FROM documents 
                WHERE title LIKE ? 
                OR authors LIKE ? 
                OR abstract LIKE ? 
                OR keywords LIKE ?
                LIMIT ?
            '''
            
            search_pattern = f"%{query}%"
            cursor.execute(search_query, (search_pattern, search_pattern, search_pattern, search_pattern, limit))
            rows = cursor.fetchall()
            
            # 결과를 딕셔너리 리스트로 변환
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in rows:
                result = dict(zip(columns, row))
                # JSON 문자열을 리스트로 변환
                for field in ['authors', 'keywords', 'citations', 'references', 'categories', 'tags']:
                    if field in result and result[field]:
                        result[field] = json.loads(result[field])
                results.append(result)
            
            return results 