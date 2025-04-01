import os
import json
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# .env 파일 로드
load_dotenv()

class DeepSeekAPI:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY가 설정되지 않았습니다.")
        print(f"DeepSeek API 초기화 완료 (API Key: {self.api_key[:8]}...)")
        
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.models = [
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "description": "기본 대화 모델"},
            {"id": "deepseek-coder", "name": "DeepSeek Coder", "description": "코딩 특화 모델"}
        ]

    def get_available_models(self) -> List[Dict[str, str]]:
        return self.models

    async def generate_response(self, user_input: str, chat_history: Optional[List[Dict[str, str]]] = None, context_docs: Optional[List[str]] = None, model_id: str = "deepseek-chat") -> str:
        print(f"API 요청 시작 - 모델: {model_id}")
        print(f"사용자 입력: {user_input}")
        
        # 시스템 프롬프트 구성
        system_prompt = "당신은 논문과 연구에 대해 잘 알고 있는 AI 어시스턴트입니다. "
        if context_docs:
            system_prompt += "다음 문서들을 참고하여 답변해주세요:\n\n"
            for doc in context_docs:
                system_prompt += f"{doc}\n\n"
        
        # 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]
        
        # 채팅 기록 추가
        if chat_history:
            for msg in chat_history[-10:]:  # 최근 10개 메시지만 사용
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({"role": "user", "content": user_input})
        
        print(f"전송할 메시지: {json.dumps(messages, ensure_ascii=False)}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=30.0
                )
                
                print(f"API 응답 상태 코드: {response.status_code}")
                response_data = response.json()
                print(f"API 응답 데이터: {json.dumps(response_data, ensure_ascii=False)}")
                
                if response.status_code == 200 and "choices" in response_data:
                    return response_data["choices"][0]["message"]["content"]
                else:
                    error_message = response_data.get("error", {}).get("message", "알 수 없는 오류가 발생했습니다.")
                    print(f"API 오류: {error_message}")
                    return f"죄송합니다. API 호출 중 오류가 발생했습니다: {error_message}"
                    
        except Exception as e:
            print(f"API 호출 중 예외 발생: {str(e)}")
            return f"죄송합니다. API 호출 중 오류가 발생했습니다: {str(e)}" 