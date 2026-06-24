const API_URL = 'http://127.0.0.1:8000';

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-upload');
const uploadStatus = document.getElementById('upload-status');
const uploadText = document.getElementById('upload-text');
const papersList = document.getElementById('papers-list');
const sessionsList = document.getElementById('sessions-list');
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const modeBtns = document.querySelectorAll('.mode-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const currentSessionTitle = document.getElementById('current-session-title');
const aiModeSelect = document.getElementById('ai-mode-select');

let isUploading = false;
let currentSessionId = null;

marked.setOptions({
    breaks: true,
    gfm: true
});

// --- Initialization ---

const initApp = async () => {
    await loadAiMode();
    await loadKnowledgeBase();
    await loadSessions();
};

const updateModeUI = (mode) => {
    const notice = document.getElementById('privacy-notice');
    const noticeText = document.getElementById('privacy-notice-text');
    
    aiModeSelect.style.display = 'inline-block';
    aiModeSelect.value = mode;
    
    if (mode === 'cloud') {
        aiModeSelect.className = 'mode-badge cloud-mode';
        notice.style.display = 'none';
    } else if (mode === 'hybrid') {
        aiModeSelect.className = 'mode-badge hybrid-mode';
        notice.style.display = 'block';
        noticeText.innerText = 'Hybrid Mode Active — your documents are indexed locally, but retrieved chunks are sent to the cloud model for answering.';
    } else if (mode === 'private') {
        aiModeSelect.className = 'mode-badge private-mode';
        notice.style.display = 'block';
        noticeText.innerText = 'Private Mode Active — all documents and questions are processed 100% locally.';
    }
};

const loadAiMode = async () => {
    try {
        const response = await fetch(`${API_URL}/settings/ai-mode`);
        if (!response.ok) return;
        const settings = await response.json();
        updateModeUI(settings.mode || settings.ai_mode || 'cloud');
    } catch (err) {
        console.error("Failed to fetch AI Mode settings", err);
    }
};

aiModeSelect.addEventListener('change', async (e) => {
    const newMode = e.target.value;
    try {
        const response = await fetch(`${API_URL}/settings/ai-mode`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: newMode })
        });
        if (response.ok) {
            updateModeUI(newMode);
            await loadKnowledgeBase();
            addMessage(`*AI Mode switched to **${newMode.toUpperCase()}***`, false, null, true);
        } else {
            alert("Failed to update AI mode on the server.");
            await loadAiMode(); // Revert
        }
    } catch (err) {
        console.error("Failed to update AI Mode", err);
        await loadAiMode(); // Revert
    }
});

// --- Sessions Logic ---

const loadSessions = async () => {
    try {
        const response = await fetch(`${API_URL}/sessions`);
        if (!response.ok) throw new Error("Failed to load sessions");
        
        const sessions = await response.json();
        sessionsList.innerHTML = "";
        
        if (sessions.length === 0) {
            await createNewSession();
        } else {
            sessions.forEach(session => addSessionToList(session.id, session.title));
            if (!currentSessionId) {
                await loadSessionChat(sessions[0].id, sessions[0].title);
            }
        }
    } catch (err) {
        console.error("Error loading sessions:", err);
    }
};

const createNewSession = async () => {
    try {
        const response = await fetch(`${API_URL}/sessions`, { method: 'POST' });
        const session = await response.json();
        
        addSessionToList(session.id, session.title, true);
        await loadSessionChat(session.id, session.title);
    } catch (err) {
        console.error("Error creating session:", err);
    }
};

const addSessionToList = (id, title, prepend = false) => {
    const div = document.createElement('div');
    div.className = `session-item ${id === currentSessionId ? 'active' : ''}`;
    div.dataset.id = id;
    
    div.innerHTML = `
        <i class="fa-regular fa-message"></i>
        <span class="session-title" title="${title}">${title}</span>
        <i class="fa-solid fa-trash delete-session-btn" title="Delete Chat"></i>
    `;
    
    div.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-session-btn')) {
            deleteSession(id, div);
        } else if (id !== currentSessionId) {
            loadSessionChat(id, title);
        }
    });
    
    if (prepend) {
        sessionsList.prepend(div);
    } else {
        sessionsList.appendChild(div);
    }
};

const updateActiveSessionUI = (id, title) => {
    currentSessionId = id;
    currentSessionTitle.innerText = title;
    
    document.querySelectorAll('.session-item').forEach(el => {
        if (parseInt(el.dataset.id) === id) {
            el.classList.add('active');
            el.querySelector('.session-title').innerText = title;
        } else {
            el.classList.remove('active');
        }
    });
};

const loadSessionChat = async (id, title) => {
    updateActiveSessionUI(id, title);
    
    const welcomeHtml = document.querySelector('.welcome-message').outerHTML;
    chatMessages.innerHTML = welcomeHtml;
    
    try {
        const response = await fetch(`${API_URL}/sessions/${id}/chat`);
        const messages = await response.json();
        
        messages.forEach(msg => {
            const isUser = msg.role === 'user';
            addMessage(msg.content, isUser, msg.sources, false);
        });
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (err) {
        console.error("Error loading chat history:", err);
    }
};

const deleteSession = async (id, element) => {
    if (!confirm("Are you sure you want to delete this chat session?")) return;
    
    try {
        const response = await fetch(`${API_URL}/sessions/${id}`, { method: 'DELETE' });
        if (response.ok) {
            element.remove();
            if (currentSessionId === id) {
                currentSessionId = null;
                await loadSessions();
            }
        }
    } catch (err) {
        console.error(err);
    }
};

newChatBtn.addEventListener('click', createNewSession);

// --- Knowledge Base Logic ---

const loadKnowledgeBase = async () => {
    try {
        const response = await fetch(`${API_URL}/papers`);
        if (!response.ok) throw new Error("Failed to load papers");
        
        const papers = await response.json();
        papersList.innerHTML = "";
        papers.forEach(paper => addPaperToList(paper.id, paper.title));
    } catch (err) {
        console.error("Error loading knowledge base:", err);
    }
};

const deletePaper = async (id, element) => {
    if (!confirm("Are you sure you want to delete this paper from the AI's memory?")) return;
    
    element.style.opacity = '0.5';
    
    try {
        const response = await fetch(`${API_URL}/papers/${id}`, { method: 'DELETE' });
        if (response.ok) {
            element.remove();
        } else {
            alert("Failed to delete paper");
            element.style.opacity = '1';
        }
    } catch (err) {
        console.error(err);
        alert("Connection error while deleting paper");
        element.style.opacity = '1';
    }
};

const addPaperToList = (id, title) => {
    const paperDiv = document.createElement('div');
    paperDiv.className = 'paper-item';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'paper-checkbox';
    checkbox.value = id;
    checkbox.checked = true;
    checkbox.title = "Uncheck to ignore this paper in chat";
    checkbox.style.marginRight = '12px';
    checkbox.style.cursor = 'pointer';
    
    const icon = document.createElement('i');
    icon.className = 'fa-solid fa-file-pdf';
    icon.style.marginRight = '8px';
    
    const titleSpan = document.createElement('span');
    titleSpan.title = title;
    titleSpan.innerText = title;
    titleSpan.style.flexGrow = '1';
    titleSpan.style.whiteSpace = 'nowrap';
    titleSpan.style.overflow = 'hidden';
    titleSpan.style.textOverflow = 'ellipsis';
    
    const deleteBtn = document.createElement('i');
    deleteBtn.className = 'fa-solid fa-trash delete-btn';
    deleteBtn.title = 'Delete Paper';
    deleteBtn.style.cursor = 'pointer';
    deleteBtn.style.color = 'var(--danger)';
    deleteBtn.style.fontSize = '14px';
    deleteBtn.style.marginLeft = '12px';
    
    deleteBtn.addEventListener('click', () => deletePaper(id, paperDiv));
    
    paperDiv.appendChild(checkbox);
    paperDiv.appendChild(icon);
    paperDiv.appendChild(titleSpan);
    paperDiv.appendChild(deleteBtn);
    
    papersList.prepend(paperDiv);
};

const handleUpload = async (file) => {
    if (!file || isUploading) return;
    
    isUploading = true;
    dropZone.classList.add('hidden');
    uploadStatus.classList.remove('hidden');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_URL}/papers/upload`, {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (response.ok) {
            uploadText.innerText = 'Upload Complete!';
            uploadStatus.style.color = 'var(--success)';
            document.querySelector('.spinner').style.display = 'none';
            addPaperToList(data.id, data.title || file.name);
            addMessage(`Successfully uploaded **${file.name}**! The document is being processed in the background. You can now ask me questions about it.`, false);
        } else {
            throw new Error(data.detail || 'Upload failed');
        }
    } catch (err) {
        uploadText.innerText = 'Upload Failed';
        uploadStatus.style.color = 'var(--danger)';
        document.querySelector('.spinner').style.display = 'none';
        addMessage(`Failed to upload paper: ${err.message}`, false);
    } finally {
        isUploading = false;
        setTimeout(() => {
            dropZone.classList.remove('hidden');
            uploadStatus.classList.add('hidden');
            uploadText.innerText = 'Processing paper...';
            uploadStatus.style.color = '';
            document.querySelector('.spinner').style.display = 'block';
            fileInput.value = '';
        }, 3000);
    }
};

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleUpload(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleUpload(e.target.files[0]);
    }
});

// --- Chat Logic ---

const addMessage = (content, isUser = false, sources = null, scroll = true) => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    
    const parsedContent = isUser ? content : marked.parse(content);
    
    let innerHTML = `
        <div class="message-avatar">
            <i class="fa-solid ${isUser ? 'fa-user' : 'fa-robot'}"></i>
        </div>
        <div class="message-content markdown-body">
            ${isUser ? `<p>${parsedContent}</p>` : parsedContent}
    `;

    if (sources && sources.length > 0) {
        innerHTML += `<div class="citations">`;
        sources.forEach(src => {
            const b64Content = src.content ? btoa(encodeURIComponent(src.content)) : "";
            let chipContent = `<i class="fa-regular fa-file-pdf"></i> ${src.paper_title} (p. ${src.page_number})`;
            if (src.image_path && src.image_path !== "None") {
                const imgUrl = `${API_URL}/images/${src.image_path}`;
                chipContent = `<img src="${imgUrl}" style="height: 18px; width: 18px; object-fit: cover; border-radius: 2px; margin-right: 6px; vertical-align: middle;"> ${src.paper_title} (p. ${src.page_number})`;
            }
            innerHTML += `<span class="citation-chip" data-file="${src.paper_title}" data-page="${src.page_number}" data-snippet="${b64Content}" title="Similarity: ${(src.similarity * 100).toFixed(1)}%">
                ${chipContent}
            </span>`;
        });
        innerHTML += `</div>`;
    }

    innerHTML += `</div>`;
    msgDiv.innerHTML = innerHTML;
    chatMessages.appendChild(msgDiv);
    
    if (scroll) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    if (!isUser && window.MathJax) {
        MathJax.typesetPromise([msgDiv]).catch((err) => console.log('MathJax error: ', err));
    }
};

const showTypingIndicator = () => {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message typing-msg';
    msgDiv.id = 'typing-indicator';
    msgDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fa-solid fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
};

const removeTypingIndicator = () => {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
};

chatInput.addEventListener('input', () => {
    sendBtn.disabled = chatInput.value.trim().length === 0;
});

const sendChatRequest = async (questionText, mode = "chat", isUserVisible = true) => {
    if (!currentSessionId) return;

    const checkedBoxes = document.querySelectorAll('.paper-checkbox:checked');
    const paperIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value));
    
    if (mode === "compare" && paperIds.length > 0 && paperIds.length < 2) {
        alert("Please select at least 2 papers to compare them.");
        return;
    }
    
    if (isUserVisible && questionText) {
        addMessage(questionText, true);
    } else if (isUserVisible && mode !== "chat") {
        const modeName = mode.charAt(0).toUpperCase() + mode.slice(1).replace('_', ' ');
        addMessage(`*[Ran ${modeName} on selected papers]*`, true);
    }
    
    showTypingIndicator();
    
    try {
        const payload = { 
            session_id: currentSessionId,
            question: questionText || "",
            paper_ids: paperIds,
            mode: mode
        };
        
        const response = await fetch(`${API_URL}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        removeTypingIndicator();
        
        if (!response.ok) {
            const data = await response.json();
            addMessage(`**Error:** ${data.detail || 'Failed to get an answer'}`, false);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai-message';
        msgDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="message-content markdown-body">
                <div class="streaming-content"></div>
                <div class="citations"></div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        
        const contentDiv = msgDiv.querySelector('.streaming-content');
        const citationsDiv = msgDiv.querySelector('.citations');
        
        let fullAnswer = "";
        let sourcesData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (!line.trim()) continue;
                
                try {
                    const parsed = JSON.parse(line);
                    
                    if (parsed.type === "sources") {
                        sourcesData = parsed.data;
                        if (sourcesData && sourcesData.length > 0) {
                            let citationsHtml = '';
                            sourcesData.forEach(src => {
                                const b64Content = src.content ? btoa(encodeURIComponent(src.content)) : "";
                                let chipContent = `<i class="fa-regular fa-file-pdf"></i> ${src.paper_title} (p. ${src.page_number})`;
                                if (src.image_path && src.image_path !== "None") {
                                    const imgUrl = `${API_URL}/images/${src.image_path}`;
                                    chipContent = `<img src="${imgUrl}" style="height: 18px; width: 18px; object-fit: cover; border-radius: 2px; margin-right: 6px; vertical-align: middle;"> ${src.paper_title} (p. ${src.page_number})`;
                                }
                                citationsHtml += `<span class="citation-chip" data-file="${src.paper_title}" data-page="${src.page_number}" data-snippet="${b64Content}" title="Similarity: ${(src.similarity * 100).toFixed(1)}%">
                                    ${chipContent}
                                </span>`;
                            });
                            citationsDiv.innerHTML = citationsHtml;
                        }
                    } else if (parsed.type === "token") {
                        fullAnswer += parsed.data;
                        contentDiv.innerHTML = marked.parse(fullAnswer);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                } catch (e) {
                    console.error("Failed to parse stream chunk", e, line);
                }
            }
        }
        
        if (window.MathJax) {
            MathJax.typesetPromise([msgDiv]).catch((err) => console.log('MathJax error: ', err));
        }

        if (currentSessionTitle.innerText === "New Chat" && questionText) {
            const newTitle = questionText.slice(0, 50);
            updateActiveSessionUI(currentSessionId, newTitle);
        }
    } catch (err) {
        removeTypingIndicator();
        addMessage(`**Connection error:** Make sure the backend is running.`, false);
    }
};

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;
    
    chatInput.value = '';
    sendBtn.disabled = true;
    sendChatRequest(question, "chat", true);
});

modeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const mode = btn.getAttribute('data-mode');
        sendChatRequest("", mode, true);
    });
});

// Start app
initApp();

// PDF Viewer Event Listener
chatMessages.addEventListener('click', (e) => {
    const chip = e.target.closest('.citation-chip');
    if (chip) {
        const file = chip.dataset.file;
        const page = parseInt(chip.dataset.page);
        let snippet = "";
        if (chip.dataset.snippet) {
            try {
                snippet = decodeURIComponent(atob(chip.dataset.snippet));
            } catch(e) {}
        }
        if (typeof openPdfViewer === 'function') openPdfViewer(file, page, snippet);
    }
});




