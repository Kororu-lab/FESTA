from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import uvicorn
from pathlib import Path
import json
from typing import List, Dict, Optional
import os
import uuid
from datetime import datetime
import re
import secrets

from .utils.document_processor import DocumentProcessor
from .utils.database import Database
from .utils.llm import DeepSeekAPI
from .models.document import Document

app = FastAPI(title="FESTA - 논문 Q&A 시스템")

# 정적 파일과 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 초기화
BASE_DIR = Path(__file__).resolve().parent.parent
document_processor = DocumentProcessor(str(BASE_DIR))
database = Database(str(BASE_DIR / "data" / "db" / "documents.db"))
llm = DeepSeekAPI()

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chat_histories: Dict[str, List[Dict[str, str]]] = {}
        self.reconnect_tokens: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        print(f"클라이언트 연결됨: {client_id}")
        self.active_connections[client_id] = websocket

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"클라이언트 연결 종료: {client_id}")

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/models")
async def get_available_models():
    """사용 가능한 모델 목록을 반환합니다."""
    return llm.get_available_models()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, client_id: str, reconnect_token: str = None):
    await manager.connect(websocket, client_id)
    try:
        # 재연결 토큰이 있는 경우 채팅 기록 전송
        if reconnect_token and reconnect_token in manager.chat_histories:
            await websocket.send_json({
                "type": "chat_history",
                "history": manager.chat_histories[reconnect_token]
            })
        
        # 새로운 재연결 토큰 생성 및 전송
        new_token = secrets.token_urlsafe(32)
        manager.chat_histories[new_token] = []
        await websocket.send_json({
            "type": "reconnect_token",
            "token": new_token
        })
        
        while True:
            try:
                data = await websocket.receive_json()
                print(f"받은 메시지: {data}")
                
                if data["type"] == "message":
                    content = data["content"]
                    model = data.get("model", "deepseek-chat")
                    
                    # 구조화된 메시지를 텍스트로 변환
                    if isinstance(content, list):
                        text_content = ""
                        for block in content:
                            if block["type"] == "code":
                                text_content += f"\n```{block.get('language', '')}\n{block['content']}\n```\n"
                            elif block["type"] == "math":
                                if block["display"]:
                                    text_content += f"\n$${block['content']}$$\n"
                                else:
                                    text_content += f"${block['content']}$"
                            else:
                                text_content += block["content"] + " "
                        content = text_content.strip()
                    
                    # 채팅 기록에 사용자 메시지 추가
                    if new_token in manager.chat_histories:
                        manager.chat_histories[new_token].append({
                            "role": "user",
                            "content": content
                        })
                    
                    try:
                        print(f"DeepSeek API 호출: {content}")
                        # AI 응답 생성
                        response = await llm.generate_response(content)
                        print(f"DeepSeek API 응답: {response}")
                        
                        # 응답을 블록으로 구조화
                        blocks = []
                        current_block = {"type": "text", "content": ""}
                        
                        lines = response.split("\n")
                        in_code_block = False
                        code_content = []
                        code_lang = ""
                        
                        for line in lines:
                            if line.startswith("```"):
                                if in_code_block:
                                    # 코드 블록 종료
                                    if current_block["content"]:
                                        blocks.append(current_block)
                                        current_block = {"type": "text", "content": ""}
                                    blocks.append({
                                        "type": "code",
                                        "language": code_lang,
                                        "content": "\n".join(code_content)
                                    })
                                    in_code_block = False
                                    code_content = []
                                else:
                                    # 코드 블록 시작
                                    if current_block["content"]:
                                        blocks.append(current_block)
                                        current_block = {"type": "text", "content": ""}
                                    in_code_block = True
                                    code_lang = line[3:].strip()
                            elif in_code_block:
                                code_content.append(line)
                            else:
                                # 수식 처리
                                math_parts = re.split(r'(\$\$[\s\S]*?\$\$|\$[^\$\n]+\$)', line)
                                for part in math_parts:
                                    if part.startswith("$$"):
                                        if current_block["content"]:
                                            blocks.append(current_block)
                                            current_block = {"type": "text", "content": ""}
                                        blocks.append({
                                            "type": "math",
                                            "display": True,
                                            "content": part[2:-2].strip()
                                        })
                                    elif part.startswith("$"):
                                        if current_block["content"]:
                                            blocks.append(current_block)
                                            current_block = {"type": "text", "content": ""}
                                        blocks.append({
                                            "type": "math",
                                            "display": False,
                                            "content": part[1:-1].strip()
                                        })
                                    elif part:
                                        current_block["content"] += part + " "
                        
                        # 마지막 블록 추가
                        if current_block["content"]:
                            blocks.append(current_block)
                        
                        # 응답 전송
                        await websocket.send_json({
                            "type": "message",
                            "content": blocks,
                            "model": model
                        })
                        
                        # 채팅 기록에 AI 응답 추가
                        if new_token in manager.chat_histories:
                            manager.chat_histories[new_token].append({
                                "role": "assistant",
                                "content": blocks,
                                "model": model
                            })
                            
                    except Exception as e:
                        print(f"API 오류: {str(e)}")
                        await websocket.send_json({
                            "type": "error",
                            "content": f"오류가 발생했습니다: {str(e)}"
                        })
                        
            except json.JSONDecodeError as e:
                print(f"JSON 디코딩 오류: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": "잘못된 메시지 형식입니다."
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        
    except Exception as e:
        print(f"WebSocket 오류: {str(e)}")
        manager.disconnect(websocket, client_id)
        try:
            await websocket.send_json({
                "type": "error",
                "content": "죄송합니다. 오류가 발생했습니다.",
                "error": str(e)
            })
        except:
            pass

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 파일 저장 경로 설정
        upload_dir = BASE_DIR / "data" / "papers"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        file_extension = os.path.splitext(file.filename)[1]
        saved_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / saved_filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 문서 처리
        processed_data = document_processor.process_document(str(file_path))
        
        # 데이터베이스에 저장
        document_data = {
            "original_filename": file.filename,
            "saved_filename": saved_filename,
            "file_path": str(file_path),
            "file_type": file_extension[1:],
            "upload_date": datetime.now().isoformat(),
            "file_size": len(content),
            "processed_file": processed_data.get("processed_file"),
            "text_length": processed_data.get("text_length"),
            "processed_date": datetime.now().isoformat(),
            "title": processed_data.get("title"),
            "authors": processed_data.get("authors"),
            "abstract": processed_data.get("abstract"),
            "keywords": processed_data.get("keywords"),
            "publication_date": processed_data.get("publication_date"),
            "journal": processed_data.get("journal"),
            "doi": processed_data.get("doi"),
            "citations": processed_data.get("citations"),
            "categories": processed_data.get("categories"),
            "tags": processed_data.get("tags"),
            "vector_id": processed_data.get("vector_id"),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        doc_id = database.insert_document(document_data)
        
        return {"message": "파일이 성공적으로 업로드되었습니다.", "doc_id": doc_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    document = database.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    return document

@app.get("/search")
async def search_documents(query: str, limit: int = 10):
    results = database.search_documents(query, limit)
    return results

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    success = database.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    return {"message": "문서가 성공적으로 삭제되었습니다."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 