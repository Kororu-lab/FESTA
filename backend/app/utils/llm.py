import os
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class DeepSeekAPI:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY가 설정되지 않았습니다.")
        
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_response(self, 
                         prompt: str, 
                         context: List[Dict[str, Any]] = None,
                         max_tokens: int = 1000,
                         temperature: float = 0.7) -> str:
        """
        DeepSeek API를 사용하여 응답을 생성합니다.
        
        Args:
            prompt: 사용자 질문
            context: 관련 문서 컨텍스트
            max_tokens: 최대 토큰 수
            temperature: 응답의 창의성 정도 (0.0 ~ 1.0)
            
        Returns:
            생성된 응답 텍스트
        """
        # 컨텍스트가 있는 경우 프롬프트 구성
        if context:
            context_text = "\n\n".join([
                f"문서: {doc.get('title', '제목 없음')}\n{doc.get('text', '')}"
                for doc in context
            ])
            full_prompt = f"""다음 문서들을 참고하여 질문에 답변해주세요:

{context_text}

질문: {prompt}

답변:"""
        else:
            full_prompt = prompt

        # API 요청 데이터 구성
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "당신은 논문 Q&A 시스템의 AI 어시스턴트입니다. 주어진 문서들을 참고하여 질문에 정확하고 명확하게 답변해주세요."},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"DeepSeek API 호출 중 오류 발생: {str(e)}") 