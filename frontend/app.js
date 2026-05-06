// GeekBrain AI Assistant — Frontend Logic
const API_URL = window.GEEKBRAIN_API_URL || '';
const messagesEl = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menu-toggle');

// Auto-resize textarea
chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
});

// Enter to send, Shift+Enter for newline
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleChatSubmit();
    }
});

// Sidebar toggle (mobile)
menuToggle.addEventListener('click', () => sidebar.classList.toggle('open'));

// Quick prompts
document.querySelectorAll('.prompt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        chatInput.value = btn.dataset.prompt;
        chatInput.dispatchEvent(new Event('input')); // For auto-resize
        handleChatSubmit();
        sidebar.classList.remove('open');
    });
});

// Submit logic extracted to prevent default browser behavior issues
async function handleChatSubmit() {
    const question = chatInput.value.trim();
    if (!question) return;

    // Clear welcome
    const welcome = messagesEl.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    addMessage('user', question);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;
    setStatus('loading', 'Thinking...');

    const typingEl = addTypingIndicator();

    try {
        const data = await sendQuestion(question);
        typingEl.remove();
        addMessage('assistant', data.answer, data.sources || []);
        setStatus('ready', 'Ready');
    } catch (err) {
        typingEl.remove();
        addMessage('assistant', `❌ Error: ${err.message}`);
        setStatus('error', 'Error');
        setTimeout(() => setStatus('ready', 'Ready'), 3000);
    } finally {
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// Submit handler
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleChatSubmit();
});

async function sendQuestion(question) {
    if (!API_URL) {
        throw new Error('API URL not configured. Set window.GEEKBRAIN_API_URL');
    }
    const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
    });
    if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`API returned ${res.status}: ${errBody}`);
    }
    return res.json();
}

function addMessage(role, text, sources = []) {
    const avatar = role === 'user' ? '👤' : '🧠';
    const div = document.createElement('div');
    div.className = `message ${role}`;

    // Simple markdown-like formatting
    const formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');

    let sourcesHtml = '';
    if (sources.length > 0) {
        const tags = sources.map(s =>
            `<span class="source-tag"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M4 1h8a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V2a1 1 0 011-1zm1 3v2h6V4H5zm0 4v1h6V8H5z"/></svg>${s}</span>`
        ).join('');
        sourcesHtml = `<div class="message-sources">${tags}</div>`;
    }

    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-bubble"><p>${formatted}</p></div>
            ${sourcesHtml}
        </div>
    `;

    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
}

function addTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.innerHTML = `
        <div class="message-avatar">🧠</div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="typing-indicator"><span></span><span></span><span></span></div>
            </div>
        </div>
    `;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
}

function setStatus(state, text) {
    statusDot.className = 'status-dot' + (state !== 'ready' ? ` ${state}` : '');
    statusText.textContent = text;
}
