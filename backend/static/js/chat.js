// WebSocket 연결 관리
let ws = null;
let currentChatId = null;
let chats = JSON.parse(localStorage.getItem('chats') || '[]');
let isWaitingResponse = false;
let clientId = localStorage.getItem('clientId');
let reconnectToken = localStorage.getItem('reconnectToken');
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;
let currentModel = 'deepseek-chat';
let availableModels = [];
let isConnected = false;

// 마크다운 설정
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

// LaTeX 설정
function renderMathInElement(element) {
    renderMathInElement(element, {
        delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false},
            {left: '\\[', right: '\\]', display: true},
            {left: '\\(', right: '\\)', display: false}
        ],
        throwOnError: false
    });
}

function connectWebSocket() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        appendMessage('system', '서버 연결에 실패했습니다. 페이지를 새로고침해주세요.');
        return;
    }

    if (!clientId) {
        clientId = Date.now().toString();
        localStorage.setItem('clientId', clientId);
    }

    const wsUrl = new URL('/ws/chat', window.location.href);
    wsUrl.protocol = wsUrl.protocol.replace('http', 'ws');
    wsUrl.searchParams.append('client_id', clientId);
    if (reconnectToken) {
        wsUrl.searchParams.append('reconnect_token', reconnectToken);
    }
    
    ws = new WebSocket(wsUrl.toString());
    
    ws.onopen = () => {
        console.log('WebSocket 연결됨');
        showConnectionStatus('연결됨', true);
        isConnected = true;
        reconnectAttempts = 0;
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
            case 'message':
                hideTypingIndicator();
                appendMessage('assistant', data.content, data.model);
                if (data.sources && data.sources.length > 0) {
                    appendSources(data.sources);
                }
                updateChatWithMessage('assistant', data.content, data.sources, data.model);
                isWaitingResponse = false;
                break;
                
            case 'error':
                hideTypingIndicator();
                appendMessage('system', data.content);
                isWaitingResponse = false;
                break;
                
            case 'reconnect_token':
                reconnectToken = data.token;
                localStorage.setItem('reconnectToken', reconnectToken);
                break;
                
            case 'chat_history':
                if (data.history && data.history.length > 0) {
                    const chatMessages = document.getElementById('chat-messages');
                    chatMessages.innerHTML = '';
                    data.history.forEach(msg => {
                        appendMessage(msg.role, msg.content);
                    });
                }
                break;
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket 오류:', error);
        hideTypingIndicator();
        isWaitingResponse = false;
        showConnectionStatus('오류 발생', false);
    };
    
    ws.onclose = () => {
        console.log('WebSocket 연결 종료');
        hideTypingIndicator();
        isWaitingResponse = false;
        showConnectionStatus('연결 끊김', false);
        isConnected = false;
        
        // 재연결 시도
        setTimeout(() => {
            if (!isConnected) {
                console.log('WebSocket 재연결 시도...');
                connectWebSocket();
            }
        }, 3000);
    };
}

// 연결 상태 표시
function showConnectionStatus(status, isConnected) {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) {
        const newStatusElement = document.createElement('div');
        newStatusElement.id = 'connection-status';
        document.body.appendChild(newStatusElement);
    }
    
    const element = document.getElementById('connection-status');
    element.textContent = status;
    element.style.backgroundColor = isConnected ? 'rgba(16, 185, 129, 0.9)' : 'rgba(239, 68, 68, 0.9)';
    element.style.display = 'block';
    
    // 3초 후에 상태 표시를 숨깁니다
    setTimeout(() => {
        element.style.opacity = '0';
        setTimeout(() => {
            element.style.display = 'none';
            element.style.opacity = '1';
        }, 300);
    }, 3000);
}

// 모델 목록 가져오기
async function fetchAvailableModels() {
    try {
        const response = await fetch('/models');
        availableModels = await response.json();
        updateModelSelector();
    } catch (error) {
        console.error('모델 목록을 가져오는데 실패했습니다:', error);
    }
}

// 모델 선택기 UI 업데이트
function updateModelSelector() {
    const modelSelector = document.getElementById('model-selector');
    modelSelector.innerHTML = '';
    
    availableModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = `${model.name}`;
        option.title = model.description;
        modelSelector.appendChild(option);
    });
    
    // 기본 모델 설정
    if (!currentModel || !availableModels.find(m => m.id === currentModel)) {
        currentModel = 'deepseek-chat';
    }
    modelSelector.value = currentModel;
}

// 메시지 전송
function sendMessage(message) {
    if (ws && ws.readyState === WebSocket.OPEN && !isWaitingResponse) {
        // 메시지에서 코드 블록과 수식을 추출하여 구조화된 형태로 전송
        const blocks = extractBlocks(message);
        ws.send(JSON.stringify({
            type: 'message',
            content: blocks,
            model: currentModel
        }));
        showTypingIndicator();
        isWaitingResponse = true;
        updateChatWithMessage('user', blocks);
    } else if (ws.readyState !== WebSocket.OPEN) {
        appendMessage('system', '서버와의 연결이 끊어졌습니다. 재연결을 시도합니다...');
        connectWebSocket();
    }
}

// 메시지에서 코드 블록과 수식을 추출하는 함수
function extractBlocks(message) {
    const blocks = [];
    let currentPos = 0;
    let text = '';

    // 코드 블록 추출 (```로 둘러싸인 부분)
    const codeRegex = /```(\w*)\n([\s\S]*?)```/g;
    let match;

    while ((match = codeRegex.exec(message)) !== null) {
        // 코드 블록 이전의 텍스트 추가
        if (currentPos < match.index) {
            text = message.substring(currentPos, match.index).trim();
            if (text) {
                blocks.push({ type: 'text', content: text });
            }
        }

        // 코드 블록 추가
        blocks.push({
            type: 'code',
            language: match[1] || 'plaintext',
            content: match[2].trim()
        });

        currentPos = match.index + match[0].length;
    }

    // 수식 블록 추출 ($$ 또는 $ 로 둘러싸인 부분)
    const mathRegex = /(\$\$[\s\S]*?\$\$|\$[^\$\n]+\$)/g;
    message = message.substring(currentPos);
    currentPos = 0;

    while ((match = mathRegex.exec(message)) !== null) {
        // 수식 이전의 텍스트 추가
        if (currentPos < match.index) {
            text = message.substring(currentPos, match.index).trim();
            if (text) {
                blocks.push({ type: 'text', content: text });
            }
        }

        // 수식 블록 추가
        blocks.push({
            type: 'math',
            display: match[0].startsWith('$$'),
            content: match[0].replace(/\$/g, '').trim()
        });

        currentPos = match.index + match[0].length;
    }

    // 남은 텍스트 추가
    text = message.substring(currentPos).trim();
    if (text) {
        blocks.push({ type: 'text', content: text });
    }

    return blocks;
}

// 로딩 표시 관리
function showTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.classList.remove('hidden');
    }
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.classList.add('hidden');
    }
}

// 메시지 표시
function appendMessage(role, content, model = null) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    // role에 따른 추가 클래스 적용
    if (role === 'user') {
        messageDiv.classList.add('user-message');
    } else if (role === 'assistant') {
        messageDiv.classList.add('assistant-message');
    } else {
        messageDiv.classList.add('system-message');
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content markdown-content';

    // content가 배열(블록)인 경우 각 블록을 적절히 렌더링
    if (Array.isArray(content)) {
        content.forEach(block => {
            const blockElement = document.createElement('div');
            blockElement.className = 'message-block';

            switch (block.type) {
                case 'code':
                    const pre = document.createElement('pre');
                    const code = document.createElement('code');
                    if (block.language) {
                        code.className = `language-${block.language}`;
                    }
                    code.textContent = block.content;
                    pre.appendChild(code);
                    blockElement.appendChild(pre);
                    hljs.highlightElement(code);
                    break;

                case 'math':
                    if (block.display) {
                        blockElement.innerHTML = `\\[${block.content}\\]`;
                    } else {
                        blockElement.innerHTML = `\\(${block.content}\\)`;
                    }
                    renderMathInElement(blockElement);
                    break;

                case 'text':
                default:
                    blockElement.innerHTML = marked.parse(block.content);
                    break;
            }

            contentDiv.appendChild(blockElement);
        });
    } else {
        // 이전 버전과의 호환성을 위해 문자열도 처리
        contentDiv.innerHTML = marked.parse(content);
    }
    
    if (model && role === 'assistant') {
        const modelBadge = document.createElement('div');
        modelBadge.className = 'model-badge';
        const modelInfo = availableModels.find(m => m.id === model) || { name: model };
        modelBadge.textContent = `🤖 ${modelInfo.name}`;
        contentDiv.appendChild(modelBadge);
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // 스크롤을 최하단으로 이동
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

// 참조 문서 표시
function appendSources(sources) {
    if (!sources || sources.length === 0) return;
    
    const chatMessages = document.getElementById('chat-messages');
    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'sources';
    
    const titleDiv = document.createElement('div');
    titleDiv.className = 'sources-title';
    titleDiv.textContent = '참조 문서:';
    
    const ul = document.createElement('ul');
    sources.forEach(source => {
        const li = document.createElement('li');
        li.textContent = source;
        ul.appendChild(li);
    });
    
    sourcesDiv.appendChild(titleDiv);
    sourcesDiv.appendChild(ul);
    chatMessages.appendChild(sourcesDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 채팅 관리 함수들
function createNewChat() {
    const chatId = Date.now().toString();
    const chat = {
        id: chatId,
        title: '새로운 대화',
        messages: [],
        createdAt: new Date().toISOString()
    };
    chats.unshift(chat);
    saveChats();
    
    // 채팅 목록 UI 업데이트
    const chatItem = createChatListItem(chat);
    
    // 새 채팅을 목록 맨 위에 추가
    const chatList = document.getElementById('chat-list');
    if (chatList.firstChild) {
        chatList.insertBefore(chatItem, chatList.firstChild);
    } else {
        chatList.appendChild(chatItem);
    }
    
    // 새 채팅 활성화
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });
    chatItem.classList.add('active');
    
    return chatId;
}

function createChatListItem(chat) {
    const chatItem = document.createElement('div');
    chatItem.className = 'chat-item';
    chatItem.dataset.chatId = chat.id;

    const titleSpan = document.createElement('span');
    titleSpan.className = 'chat-title';
    titleSpan.textContent = chat.title;

    const optionsDiv = document.createElement('div');
    optionsDiv.className = 'chat-options';

    const optionsButton = document.createElement('button');
    optionsButton.className = 'options-button';
    optionsButton.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
        </svg>
    `;

    const optionsMenu = document.createElement('div');
    optionsMenu.className = 'options-menu';
    optionsMenu.innerHTML = `
        <button class="rename-chat">이름 바꾸기</button>
        <button class="delete-chat">삭제</button>
    `;

    optionsDiv.appendChild(optionsButton);
    optionsDiv.appendChild(optionsMenu);
    chatItem.appendChild(titleSpan);
    chatItem.appendChild(optionsDiv);

    // 채팅 아이템 클릭 이벤트
    chatItem.addEventListener('click', (e) => {
        if (!optionsDiv.contains(e.target)) {
            loadChat(chat.id);
        }
    });

    // 옵션 버튼 클릭 이벤트
    optionsButton.addEventListener('click', (e) => {
        e.stopPropagation();
        console.log('옵션 버튼 클릭됨');  // 디버깅용 로그
        
        showOptionsMenu(optionsButton, chat.id);
    });

    // 이름 바꾸기 버튼 클릭 이벤트
    optionsMenu.querySelector('.rename-chat').addEventListener('click', (e) => {
        e.stopPropagation();
        console.log('이름 바꾸기 클릭됨');  // 디버깅용 로그
        const newTitle = prompt('새로운 대화 제목을 입력하세요:', chat.title);
        if (newTitle && newTitle.trim()) {
            chat.title = newTitle.trim();
            titleSpan.textContent = chat.title;
            saveChats();
        }
        hideOptionsMenu(optionsButton);
    });

    // 삭제 버튼 클릭 이벤트
    optionsMenu.querySelector('.delete-chat').addEventListener('click', (e) => {
        e.stopPropagation();
        console.log('삭제 버튼 클릭됨');  // 디버깅용 로그
        if (confirm('이 대화를 삭제하시겠습니까?')) {
            chats = chats.filter(c => c.id !== chat.id);
            chatItem.remove();
            saveChats();
            if (currentChatId === chat.id) {
                if (chats.length > 0) {
                    loadChat(chats[0].id);
                } else {
                    currentChatId = createNewChat();
                }
            }
        }
        hideOptionsMenu(optionsButton);
    });

    return chatItem;
}

function loadChat(chatId) {
    if (currentChatId === chatId) return;
    
    currentChatId = chatId;
    const chat = chats.find(c => c.id === chatId);
    if (chat) {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = '';
        chat.messages.forEach(msg => {
            appendMessage(msg.role, msg.content, msg.model);
            if (msg.sources && msg.sources.length > 0) {
                appendSources(msg.sources);
            }
        });
        // 활성 채팅 표시
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.chatId === chatId) {
                item.classList.add('active');
            }
        });
    }
}

function updateChatWithMessage(role, content, sources = [], model = null) {
    if (!currentChatId) return;
    
    const chat = chats.find(c => c.id === currentChatId);
    if (chat) {
        chat.messages.push({ role, content, sources, model });
        if (role === 'user' && chat.messages.length === 1) {
            // 첫 메시지를 제목으로 설정
            let title = '';
            if (Array.isArray(content)) {
                // 블록 형식의 메시지에서 텍스트 추출
                title = content.map(block => {
                    if (block.type === 'text') return block.content;
                    return '';
                }).join(' ').trim();
            } else {
                title = content;
            }
            
            // 제목 길이 제한 및 말줄임표 처리
            chat.title = title.length > 30 ? title.substring(0, 30) + '...' : title;
            
            const chatItem = document.querySelector(`[data-chat-id="${chat.id}"]`);
            if (chatItem) {
                const titleSpan = chatItem.querySelector('.chat-title');
                if (titleSpan) {
                    titleSpan.textContent = chat.title;
                }
            }
        }
        saveChats();
    }
}

function saveChats() {
    localStorage.setItem('chats', JSON.stringify(chats));
}

// 이벤트 리스너 설정
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    
    // 새로운 채팅 버튼
    document.getElementById('new-chat-button').addEventListener('click', () => {
        currentChatId = createNewChat();
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = '';
    });
    
    // 메시지 전송 핸들러
    function sendMessageHandler(e) {
        if (e && e.key === 'Enter') {
            if (e.shiftKey) {
                return; // Shift+Enter는 줄바꿈 허용
            }
            e.preventDefault(); // 기본 줄바꿈 동작 방지
        }
        
        const message = messageInput.value.trim();
        if (message && !isWaitingResponse) {
            if (!currentChatId) {
                currentChatId = createNewChat();
            }
            sendMessage(message);
            messageInput.value = '';
            messageInput.style.height = 'auto'; // 입력창 높이 초기화
        }
    }
    
    // Enter 키 이벤트
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !isWaitingResponse) {
            sendMessageHandler(e);
        }
    });
    
    // 자동 높이 조절
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = messageInput.scrollHeight + 'px';
    });
    
    sendButton.addEventListener('click', () => sendMessageHandler());
    
    // 초기 채팅 목록 로드
    const chatList = document.getElementById('chat-list');
    chatList.innerHTML = '';
    chats.forEach(chat => {
        const chatItem = createChatListItem(chat);
        chatList.appendChild(chatItem);
    });
    
    // 첫 번째 채팅 또는 새 채팅 로드
    if (chats.length > 0) {
        loadChat(chats[0].id);
    } else {
        currentChatId = createNewChat();
    }

    // 모델 선택기 이벤트 리스너
    document.getElementById('model-selector').addEventListener('change', (e) => {
        currentModel = e.target.value;
        console.log('Selected model:', currentModel);
    });
    
    // 모델 목록 가져오기
    fetchAvailableModels();
});

function showOptionsMenu(button, chatId) {
    const menu = button.nextElementSibling;
    const buttonRect = button.getBoundingClientRect();
    
    // 모든 메뉴를 먼저 닫습니다
    document.querySelectorAll('.options-menu').forEach(m => {
        if (m !== menu) {
            m.style.display = 'none';
        }
    });
    
    // 메뉴 위치 설정
    menu.style.position = 'fixed';
    menu.style.left = `${buttonRect.left - 150}px`; // 메뉴 너비를 고려하여 왼쪽에 배치
    menu.style.top = `${buttonRect.bottom + 5}px`;
    
    // 화면 경계 체크
    setTimeout(() => {
        const menuRect = menu.getBoundingClientRect();
        if (menuRect.right > window.innerWidth) {
            menu.style.left = `${window.innerWidth - menuRect.width - 10}px`;
        }
        if (menuRect.left < 0) {
            menu.style.left = '10px';
        }
        if (menuRect.bottom > window.innerHeight) {
            menu.style.top = `${buttonRect.top - menuRect.height - 5}px`;
        }
    }, 0);
    
    // 메뉴 표시
    menu.style.display = 'block';
    
    // 문서 클릭 이벤트를 한 번만 등록합니다
    const closeMenu = (e) => {
        if (!menu.contains(e.target) && !button.contains(e.target)) {
            menu.style.display = 'none';
            document.removeEventListener('click', closeMenu);
        }
    };
    
    // 기존 이벤트 리스너를 제거하고 새로운 리스너를 등록합니다
    document.removeEventListener('click', closeMenu);
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 0);
}

function hideOptionsMenu(button) {
    const menu = button.nextElementSibling;
    menu.style.display = 'none';
} 