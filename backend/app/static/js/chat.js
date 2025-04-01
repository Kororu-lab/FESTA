document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const chatMessages = document.getElementById('chat-messages');
    const uploadForm = document.getElementById('uploadForm');
    const paperFile = document.getElementById('paperFile');

    let ws = null;

    // WebSocket 연결 설정
    function connectWebSocket() {
        ws = new WebSocket(`ws://${window.location.host}/ws/chat`);

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            appendMessage(message.text, message.isUser);
        };

        ws.onclose = () => {
            console.log('WebSocket 연결이 종료되었습니다.');
            setTimeout(connectWebSocket, 1000);
        };
    }

    // 메시지 전송 함수
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message && ws) {
            const messageData = {
                text: message,
                isUser: true
            };
            ws.send(JSON.stringify(messageData));
            appendMessage(message, true);
            messageInput.value = '';
        }
    }

    // 메시지 표시 함수
    function appendMessage(text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${isUser ? 'justify-end' : 'justify-start'}`;
        
        const messageBubble = document.createElement('div');
        messageBubble.className = `max-w-[70%] rounded-lg p-3 ${
            isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'
        }`;
        messageBubble.textContent = text;
        
        messageDiv.appendChild(messageBubble);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 이벤트 리스너 설정
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // 파일 업로드 처리
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = paperFile.files[0];
        if (!file) {
            alert('파일을 선택해주세요.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            appendMessage(`논문 "${result.filename}" 이(가) 업로드되었습니다.`, false);
        } catch (error) {
            console.error('업로드 중 오류 발생:', error);
            appendMessage('논문 업로드 중 오류가 발생했습니다.', false);
        }
    });

    // WebSocket 연결 시작
    connectWebSocket();
}); 