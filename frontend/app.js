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

    // ═══════ Load questions into sidebar accordion ═══════
    loadQuestionLevels();

    // Level accordion toggle
    document.querySelectorAll('.level-header').forEach(btn => {
        btn.addEventListener('click', () => {
            const group = btn.closest('.level-group');
            // Close others
            document.querySelectorAll('.level-group.open').forEach(g => {
                if (g !== group) g.classList.remove('open');
            });
            group.classList.toggle('open');
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
            pipelineTraces: response.pipeline_traces || [],
            rawCitations: response.raw_citations || [],
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
    const { tools = [], sources = [], toolDetails = [], pipelineTraces = [], rawCitations = [] } = meta;

    let modifiedText = text;
    const usedChunks = [];

    // Process citations to add markers and collect used chunks
    if (rawCitations && rawCitations.length > 0) {
        rawCitations.forEach(attr => {
            const citations = attr.citations || [];
            citations.forEach(cit => {
                const genText = cit.generatedResponsePart?.textResponsePart?.text;
                const refs = cit.retrievedReferences || [];
                
                if (genText && refs.length > 0) {
                    let citationMarkers = [];
                    refs.forEach(ref => {
                        const chunkText = ref.content?.text;
                        const uri = ref.location?.s3Location?.uri || 'unknown';
                        const filename = uri.split('/').pop();
                        
                        if (chunkText) {
                            let snippet = chunkText;
                            if (text) {
                                const paragraphs = chunkText.split(/\n\s*\n|\n/);
                                const answerWords = text.toLowerCase().match(/\b\w+\b/g) || [];
                                let bestScore = -1;
                                let bestPara = '';
                                
                                for (const p of paragraphs) {
                                    const pWords = p.toLowerCase().match(/\b\w+\b/g) || [];
                                    let score = 0;
                                    const pWordSet = new Set(pWords);
                                    for (const w of answerWords) {
                                        if (w.length > 3 && pWordSet.has(w)) score++;
                                    }
                                    if (pWords.length > 5 && score > bestScore) {
                                        bestScore = score;
                                        bestPara = p;
                                    }
                                }
                                if (bestScore > 0 && bestPara.length < chunkText.length) {
                                    snippet = bestPara.trim();
                                    if (snippet.length > 500) snippet = snippet.substring(0, 500) + '...';
                                } else {
                                    snippet = chunkText.substring(0, 500) + '...';
                                }
                            }

                            let chunkIdx = usedChunks.findIndex(c => c.filename === filename && c.text === snippet);
                            if (chunkIdx === -1) {
                                usedChunks.push({ text: snippet, filename: filename });
                                chunkIdx = usedChunks.length - 1;
                            }
                            // Only add if not already in the array
                            const marker = `[${chunkIdx + 1}]`;
                            if (!citationMarkers.includes(marker)) {
                                citationMarkers.push(marker);
                            }
                        }
                    });
                    
                    if (citationMarkers.length > 0) {
                        const markerHtml = ` <sup class="citation-marker">${citationMarkers.join(', ')}</sup>`;
                        modifiedText = modifiedText.replace(genText, genText + markerHtml);
                    }
                }
            });
        });
    }

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
    bubble.innerHTML = markdownToHtml(modifiedText);
    content.appendChild(bubble);

    // ── Meta section: sources + tools + query details + observability ──
    const hasMeta = sources.length > 0 || tools.length > 0 || toolDetails.length > 0 || pipelineTraces.length > 0;
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

        // Observability Pipeline Dashboard
        if (pipelineTraces.length > 0) {
            const obsDetails = document.createElement('details');
            obsDetails.className = 'observability-details';
            const obsSummary = document.createElement('summary');
            obsSummary.innerHTML = '🕵️‍♂️ Observability Pipeline (Traces)';
            obsDetails.appendChild(obsSummary);

            pipelineTraces.forEach((trace, idx) => {
                const stepBlock = document.createElement('div');
                stepBlock.className = 'trace-step';
                
                let stepTitle = `Step ${idx + 1}`;
                let stepContent = '';

                if (trace.modelInvocationInput) {
                    stepTitle += ' - Model Invocation Input';
                    stepContent = 'Preparing prompt for Bedrock LLM...';
                }
                else if (trace.invocationInput) {
                    stepTitle += ' - Tool Invocation';
                    const ag = trace.invocationInput.actionGroupInvocationInput;
                    if (ag) {
                        stepContent = `<strong>Function:</strong> ${ag.function}<br>`;
                        if (ag.parameters && ag.parameters.length > 0) {
                            stepContent += `<strong>Parameters:</strong> <code>${JSON.stringify(ag.parameters)}</code>`;
                        }
                    } else if (trace.invocationInput.knowledgeBaseLookupInput) {
                        stepTitle += ' - Knowledge Base Query';
                        stepContent = `<strong>Query:</strong> ${trace.invocationInput.knowledgeBaseLookupInput.text}`;
                    }
                }
                else if (trace.observation) {
                    stepTitle += ' - Observation';
                    if (trace.observation.actionGroupInvocationOutput) {
                         stepContent = `<strong>Tool Output:</strong> <code>${trace.observation.actionGroupInvocationOutput.text}</code>`;
                    } else if (trace.observation.knowledgeBaseLookupOutput) {
                         stepTitle += ' - KB Retrieved References';
                         if (usedChunks.length > 0) {
                             stepContent = `<em>Retrieved chunks from Knowledge Base. Showing ${usedChunks.length} exact chunks actually cited by the model:</em><br>`;
                             usedChunks.forEach((chunk, rIdx) => {
                                 stepContent += `<details class="kb-chunk"><summary>[${rIdx + 1}] 📄 ${chunk.filename}</summary><div class="kb-chunk-text">${chunk.text}</div></details>`;
                             });
                         } else {
                             const refs = trace.observation.knowledgeBaseLookupOutput.retrievedReferences || [];
                             stepContent = `<em>Retrieved ${refs.length} chunks from Knowledge Base.</em><br>`;
                             refs.forEach((ref, rIdx) => {
                                 const uri = ref.location?.s3Location?.uri || 'unknown';
                                 const filename = uri.split('/').pop();
                                 const text = ref.content?.text || '';
                                 stepContent += `<details class="kb-chunk"><summary>📄 ${filename}</summary><div class="kb-chunk-text">${text}</div></details>`;
                             });
                         }
                    } else if (trace.observation.finalResponse) {
                         stepTitle += ' - Final Response';
                         stepContent = `<em>LLM generated the final answer.</em>`;
                    }
                }
                else if (trace.modelInvocationOutput) {
                    stepTitle += ' - Model Invocation Output (Reasoning)';
                     try {
                         const raw = JSON.parse(trace.modelInvocationOutput.rawResponse.content);
                         const msg = raw.output.message.content[0];
                         if (msg && msg.text) {
                              let cleanText = msg.text.replace(/<[^>]*DSML[^>]*function_calls[^>]*(?:>|$)/g, '').trim();
                              if (cleanText) {
                                  if (cleanText.length > 300) cleanText = cleanText.substring(0, 300) + '...';
                                  cleanText = cleanText.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                                  cleanText = cleanText.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
                                  stepContent = `<div class="llm-reasoning">${cleanText}</div>`;
                              } else {
                                  const nextMsg = raw.output.message.content[1];
                                  if (nextMsg && nextMsg.toolUse) {
                                      stepContent = `<strong>LLM Decision:</strong> Call tool <code>${nextMsg.toolUse.name}</code>`;
                                  } else {
                                      stepContent = '<em>LLM decided to call a tool immediately.</em>';
                                  }
                              }
                         } else if (msg && msg.toolUse) {
                              stepContent = `<strong>LLM Decision:</strong> Call tool <code>${msg.toolUse.name}</code>`;
                         }
                    } catch(e) {
                         stepContent = 'LLM returned a response.';
                    }
                }

                stepBlock.innerHTML = `<div class="trace-step-title">${stepTitle}</div><div class="trace-step-content">${stepContent}</div>`;
                obsDetails.appendChild(stepBlock);
            });
            metaDiv.appendChild(obsDetails);
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

// ═══════ Load test questions into sidebar ═══════
function loadQuestionLevels() {
    const L1 = [
        { id: "L1-01", q: "What is the current API rate limit for PaymentGW?" },
        { id: "L1-02", q: "Who leads Team Platform and what services do they own?" },
        { id: "L1-03", q: "What was the root cause of the March 5, 2026 PaymentGW outage?" },
        { id: "L1-04", q: "What is GeekBrain's data retention policy for transaction logs?" },
        { id: "L1-05", q: "What are GeekBrain's production deployment windows?" },
        { id: "L1-06", q: "What authentication method does the PaymentGW API use?" },
        { id: "L1-07", q: "What message queue does NotificationSvc use?" },
        { id: "L1-08", q: "After the March 5 PaymentGW incident, a circuit breaker review was scheduled. What was the deadline?" },
        { id: "L1-09", q: "What programming language is AuthSvc written in?" },
        { id: "L1-10", q: "How often does GeekBrain rotate JWT signing keys?" },
    ];

    const L2 = [
        { id: "L2-01", q: "What is PaymentGW's API rate limit?" },
        { id: "L2-02", q: "If Team Commerce discovers a P1 bug in OrderSvc at 21:00 on a Friday, can they deploy a fix? What is the process?" },
        { id: "L2-03", q: "Which services would be directly affected if AuthSvc goes completely down?" },
        { id: "L2-04", q: "Based on the Q1 review and the cost optimization initiative, which services are the top priorities for cost reduction and why?" },
        { id: "L2-05", q: "What common lessons emerged from the March 2026 incidents at PaymentGW and FraudDetector?" },
        { id: "L2-06", q: "What should a new engineer joining Team Data know about the systems they'll work with, based on the onboarding guide and team information?" },
        { id: "L2-07", q: "The Q1 2026 review mentioned concerns about NotificationSvc. What specific issues were raised, and what does the capacity planning document propose to fix them?" },
        { id: "L2-08", q: "What is the complete escalation path for a P1 incident on PaymentGW, from detection to CTO notification? Include specific names and timeframes." },
    ];

    const L3 = [
        { id: "L3-01", q: "What is PaymentGW's current p99 latency?" },
        { id: "L3-02", q: "What was GeekBrain's total infrastructure cost across all services in Q1 2026?" },
        { id: "L3-03", q: "Which service had the highest total cost in March 2026?" },
        { id: "L3-04", q: "Is PaymentGW's current error rate within its SLA target?" },
        { id: "L3-05", q: "Compare PaymentGW's current p99 latency to its Q1 2026 daily average." },
        { id: "L3-06", q: "Is NotificationSvc currently meeting its SLA targets?" },
        { id: "L3-07", q: "How much did PaymentGW's total cost increase from Q4 2025 to Q1 2026?" },
        { id: "L3-08", q: "Which service currently handles the most requests per minute?" },
        { id: "L3-09", q: "What is FraudDetector's current CPU utilization, and how does it compare to other services?" },
        { id: "L3-10", q: "How many total incidents occurred in Q1 2026, and which service had the most?" },
    ];

    const L4 = [
        { id: "L4-01", title: "Cost Investigation", turns: [
            "Which service had the highest cost in March 2026?",
            "Why did its costs spike that month?",
            "Is it running normally right now?",
            "Which team is responsible for it?"
        ]},
        { id: "L4-02", title: "SLA Compliance Check", turns: [
            "Is NotificationSvc currently meeting its SLA targets?",
            "Has it had any incidents recently?",
            "What team owns it and who should I contact?",
            "What's their on-call rotation?"
        ]},
        { id: "L4-03", title: "Incident Follow-up", turns: [
            "Tell me about the most severe incident in Q1 2026.",
            "What exactly caused it?",
            "Was there a follow-up action with a deadline?",
            "Is that overdue?"
        ]},
        { id: "L4-04", title: "Capacity Planning", turns: [
            "What is AuthSvc's current request volume?",
            "Is that close to any planned capacity threshold?",
            "How fast has it been growing?",
            "At that growth rate, roughly when would it hit 35k?"
        ]},
        { id: "L4-05", title: "Security Review", turns: [
            "When was the last security-related incident?",
            "What went wrong?",
            "Does the security policy cover this kind of failure?",
            "What did the team change to prevent it happening again?"
        ]},
        { id: "L4-06", title: "FraudDetector Deep Dive", turns: [
            "What is FraudDetector's current error rate?",
            "Is that within its SLA?",
            "But it had a model drift issue recently, right? What happened?",
            "How often is the model retrained now?"
        ]},
    ];

    const L5 = [
        { id: "L5-01", q: "Assess whether PaymentGW is reliable and recommend improvements." },
        { id: "L5-02", q: "GeekBrain wants to cut infrastructure costs by 15% in Q2. Analyze current spending and recommend which services to optimize first." },
        { id: "L5-03", q: "Which service is most at risk of SLA breach right now? What should be done about it?" },
        { id: "L5-04", q: "Prepare a Q1 2026 reliability report card for all GeekBrain services." },
        { id: "L5-05", q: "GeekBrain is considering whether to add more engineers to Team Engagement or Team Platform. Based on current data, which team needs reinforcement more urgently and why?" },
    ];

    // Helper to create a question button
    function makeQBtn(id, text, extra) {
        const btn = document.createElement('button');
        btn.className = 'q-btn';
        btn.innerHTML = `<span class="q-id">${id}</span><span class="q-text">${text}${extra || ''}</span>`;
        btn.addEventListener('click', () => {
            chatInput.value = text;
            sendMessage();
            // Close sidebar on mobile
            if (window.innerWidth < 768) sidebar.classList.remove('open');
        });
        return btn;
    }

    // L1
    const l1Container = document.getElementById('level-1-questions');
    L1.forEach(q => l1Container.appendChild(makeQBtn(q.id, q.q)));

    // L2
    const l2Container = document.getElementById('level-2-questions');
    L2.forEach(q => l2Container.appendChild(makeQBtn(q.id, q.q)));

    // L3
    const l3Container = document.getElementById('level-3-questions');
    L3.forEach(q => l3Container.appendChild(makeQBtn(q.id, q.q)));

    // L4 — multi-turn: show each turn as separate button with turn indicator
    const l4Container = document.getElementById('level-4-questions');
    L4.forEach(conv => {
        conv.turns.forEach((turn, i) => {
            const turnLabel = `<span class="q-turn">${conv.title} · Turn ${i + 1}</span>`;
            l4Container.appendChild(makeQBtn(conv.id, turn, turnLabel));
        });
    });

    // L5
    const l5Container = document.getElementById('level-5-questions');
    L5.forEach(q => l5Container.appendChild(makeQBtn(q.id, q.q)));
}
