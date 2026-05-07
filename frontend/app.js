// ═══════════════════════════════════════
// GeekBrain AI Assistant — Frontend Logic
// Matches Build/frontend/index.html IDs
// ═══════════════════════════════════════

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatForm = document.getElementById('chat-form');
const sendBtn = document.getElementById('send-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const menuToggle = document.getElementById('menu-toggle');
const sidebar = document.getElementById('sidebar');

// API URL — injected by Terraform or fallback
const API_URL = window.GEEKBRAIN_API_URL || '';

let isWaiting = false;

// ═══════ Init ═══════
document.addEventListener('DOMContentLoaded', () => {
    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Form submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Shift+Enter for new line, Enter to send
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Sidebar toggle (mobile)
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // Quick prompt buttons
    document.querySelectorAll('.prompt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.dataset.prompt;
            sendMessage();
        });
    });

    // Check API
    checkApiStatus();
    chatInput.focus();
});

// ═══════ Check API status ═══════
async function checkApiStatus() {
    if (!API_URL) {
        statusDot.className = 'status-dot';
        statusText.textContent = 'No API configured';
        return;
    }
    try {
        const url = API_URL.endsWith('/') ? API_URL + 'chat' : API_URL + '/chat';
        await fetch(url, { method: 'OPTIONS', mode: 'cors' });
        statusDot.className = 'status-dot connected';
        statusText.textContent = 'Connected';
    } catch {
        statusDot.className = 'status-dot error';
        statusText.textContent = 'Offline';
    }
}

// ═══════ Send message ═══════
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isWaiting) return;

    // Remove welcome message
    const welcome = chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Add user message
    addMessage('user', text);

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Show thinking
    const thinkingEl = showThinking();
    isWaiting = true;
    sendBtn.disabled = true;

    try {
        const response = await callAPI(text);
        thinkingEl.remove();
        addMessage('assistant', response.answer, {
            tools: response.tools_used || [],
            sources: response.sources || [],
            toolDetails: response.tool_details || [],
        });
    } catch (err) {
        thinkingEl.remove();
        addMessage('assistant', `⚠️ Error: ${err.message}\n\nMake sure the API Gateway is configured and accessible.`);
    }

    isWaiting = false;
    sendBtn.disabled = false;
    chatInput.focus();
}

// ═══════ Call API Gateway ═══════
async function callAPI(question) {
    if (!API_URL) throw new Error('No API URL configured');

    const url = API_URL.endsWith('/') ? API_URL + 'chat' : API_URL + '/chat';

    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            question: question,
            session_id: getSessionId(),
        }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
}

// ═══════ Add message to UI ═══════
function addMessage(role, text, meta = {}) {
    const { tools = [], sources = [], toolDetails = [] } = meta;

    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    // Avatar
    const avatar = document.createElement('div');
    avatar.className = `avatar ${role === 'assistant' ? 'bot-avatar' : 'user-avatar'}`;
    avatar.textContent = role === 'assistant' ? 'G' : '👤';

    // Content wrapper
    const content = document.createElement('div');
    content.className = 'message-content';

    // Message bubble
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = markdownToHtml(text);
    content.appendChild(bubble);

    // ── Meta section: sources + tools + query details ──
    const hasMeta = sources.length > 0 || tools.length > 0 || toolDetails.length > 0;
    if (hasMeta) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';

        // Source file tags (green)
        if (sources.length > 0) {
            const srcRow = document.createElement('div');
            srcRow.className = 'meta-row';
            sources.forEach(src => {
                const tag = document.createElement('span');
                tag.className = 'source-tag';
                tag.textContent = src;
                srcRow.appendChild(tag);
            });
            metaDiv.appendChild(srcRow);
        }

        // Tool badges (purple)
        if (tools.length > 0) {
            const toolRow = document.createElement('div');
            toolRow.className = 'meta-row';
            tools.forEach(tool => {
                const badge = document.createElement('span');
                badge.className = 'tool-badge';
                badge.textContent = `🔧 ${tool}`;
                toolRow.appendChild(badge);
            });
            metaDiv.appendChild(toolRow);
        }

        // Tool details — collapsible SQL/params
        if (toolDetails.length > 0) {
            const details = document.createElement('details');
            details.className = 'tool-details';
            const summary = document.createElement('summary');
            summary.textContent = '📊 Query Details';
            details.appendChild(summary);

            toolDetails.forEach(td => {
                const block = document.createElement('div');
                block.className = 'detail-block';
                let html = `<span class="detail-tool">${td.tool}</span>`;
                if (td.parameters) {
                    Object.entries(td.parameters).forEach(([key, val]) => {
                        html += `<div class="detail-param"><span class="detail-key">${key}:</span> <code>${val}</code></div>`;
                    });
                }
                block.innerHTML = html;
                details.appendChild(block);
            });

            metaDiv.appendChild(details);
        }

        content.appendChild(metaDiv);
    }

    // Timestamp
    const time = document.createElement('span');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    content.appendChild(time);

    msg.appendChild(avatar);
    msg.appendChild(content);
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ═══════ Show thinking dots ═══════
function showThinking() {
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    msg.innerHTML = `
        <div class="avatar bot-avatar">G</div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="thinking"><span></span><span></span><span></span></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msg;
}

// ═══════ Simple markdown parser ═══════
function markdownToHtml(text) {
    if (!text) return '';
    return text
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^/, '<p>')
        .replace(/$/, '</p>');
}

// ═══════ Session management ═══════
function getSessionId() {
    let id = sessionStorage.getItem('geekbrain_session');
    if (!id) {
        id = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('geekbrain_session', id);
    }
    return id;
}
