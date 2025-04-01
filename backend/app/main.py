from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import uvicorn
from pathlib import Path
import json
from typing import List
import os

from .utils.document_processor import DocumentProcessor
from .utils.database import Database
from .utils.llm import DeepSeekAPI
from .models.document import Document

app = FastAPI(title="FESTA - 논문 Q&A 시스템")

# 정적 파일과 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 초기화
BASE_DIR = Path(__file__).parent.parent
document_processor = DocumentProcessor(str(BASE_DIR))
database = Database(str(BASE_DIR / "data" / "db" / "documents.db"))
llm = DeepSeekAPI()

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, websocket: WebSocket, message: str):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 사용자 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 메시지 타입 확인
            if message_data.get("type") == "question":
                question = message_data.get("content", "")
                
                # 관련 문서 검색
                relevant_docs = database.search_documents(question, limit=3)
                
                try:
                    # DeepSeek API를 사용하여 응답 생성
                    response = llm.generate_response(question, relevant_docs)
                    
                    # 응답 전송
                    await manager.send_message(websocket, json.dumps({
                        "type": "answer",
                        "content": response,
                        "sources": [doc.get("title", "제목 없음") for doc in relevant_docs]
                    }))
                except Exception as e:
                    await manager.send_message(websocket, json.dumps({
                        "type": "error",
                        "content": f"응답 생성 중 오류가 발생했습니다: {str(e)}"
                    }))
            else:
                await manager.send_message(websocket, json.dumps({
                    "type": "error",
                    "content": "지원하지 않는 메시지 타입입니다."
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except json.JSONDecodeError:
        await manager.send_message(websocket, json.dumps({
            "type": "error",
            "content": "잘못된 JSON 형식입니다."
        }))
    except Exception as e:
        await manager.send_message(websocket, json.dumps({
            "type": "error",
            "content": f"오류가 발생했습니다: {str(e)}"
        }))

@app.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    try:
        # 파일 내용 읽기
        content = await file.read()
        
        # 문서 저장 및 메타데이터 생성
        metadata = document_processor.save_document(content, file.filename)
        
        # 문서 처리
        file_path = Path(metadata["file_path"])
        processing_result = document_processor.process_document(file_path)
        
        # 메타데이터와 처리 결과 병합
        document_data = {**metadata, **processing_result}
        
        # 데이터베이스에 저장
        doc_id = database.insert_document(document_data)
        
        return {
            "message": "문서가 성공적으로 업로드되었습니다.",
            "document_id": doc_id,
            "metadata": document_data
        }
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