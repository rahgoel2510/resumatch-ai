/**
 * ═══════════════════════════════════════════════════════════════════════
 * RG Aide — Main Logic
 * Copyright (c) 2026 Rahul Goel. MIT License.
 * ═══════════════════════════════════════════════════════════════════════
 *
 * FEATURES:
 *  • Chat with free AI models (streamed responses)
 *  • Page context: reads current tab and includes it with messages
 *  • Suggested prompts (quick action chips)
 *  • Copy / Regenerate buttons on AI messages
 *  • File attachments (reads text files into context)
 *  • Slash commands (/summarize, /extract, /help)
 *  • Professional settings panel
 *  • Session-based private memory (RAM only)
 *
 * ARCHITECTURE:
 *  state → one object holds everything (inspect via window.__state)
 *  dom   → all DOM references in one place
 *  boot  → load key → show setup or chat
 *
 * ═══════════════════════════════════════════════════════════════════════
 */
'use strict';
document.addEventListener('DOMContentLoaded', main);

function main() {

  // ═══════════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════════
  const API_BASE = 'https://openrouter.ai/api/v1';

  const state = {
    apiKey: '',
    model: '',
    models: [],
    sessionMemory: [],    // {role, content}[] — sent with each request
    isStreaming: false,
    pageContext: '',       // Current page text (when user clicks page btn)
    pageContextActive: false,
    attachments: [],      // {name, content}[] — file text
    settings: { sessionMem: true, autoCtx: false, compact: false }
  };
  window.__state = state;

  // ═══════════════════════════════════════════════════════════════════
  // DOM REFERENCES
  // ═══════════════════════════════════════════════════════════════════
  const dom = {
    setupScreen: document.getElementById('setupScreen'),
    chatScreen: document.getElementById('chatScreen'),
    apiKeyInput: document.getElementById('apiKeyInput'),
    saveKeyBtn: document.getElementById('saveKeyBtn'),
    keyError: document.getElementById('keyError'),

    modelSelect: document.getElementById('modelSelect'),
    newChatBtn: document.getElementById('newChatBtn'),
    settingsBtn: document.getElementById('settingsBtn'),

    chatArea: document.getElementById('chatArea'),
    welcomeState: document.getElementById('welcomeState'),
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    pageCtxBtn: document.getElementById('pageCtxBtn'),
    attachBtn: document.getElementById('attachBtn'),
    attachBar: document.getElementById('attachBar'),
    memoryCount: document.getElementById('memoryCount'),
    fileInput: document.getElementById('fileInput'),

    settingsPanel: document.getElementById('settingsPanel'),
    settingsBackdrop: document.getElementById('settingsBackdrop'),
    settingsCloseBtn: document.getElementById('settingsCloseBtn'),
    settingsModelSelect: document.getElementById('settingsModelSelect'),
    settingsKeyInput: document.getElementById('settingsKeyInput'),
    settingsKeySave: document.getElementById('settingsKeySave'),
    settingsKeyStatus: document.getElementById('settingsKeyStatus'),
    settingsSessionMem: document.getElementById('settingsSessionMem'),
    settingsAutoCtx: document.getElementById('settingsAutoCtx'),
    settingsCompact: document.getElementById('settingsCompact'),
  };

  // ═══════════════════════════════════════════════════════════════════
  // CONFIG (load/save from chrome.storage)
  // ═══════════════════════════════════════════════════════════════════
  function loadKey() {
    return new Promise(r => chrome.storage.local.get(['rg_api_key', 'rg_settings'], d => {
      if (d.rg_settings) Object.assign(state.settings, d.rg_settings);
      r(d.rg_api_key || null);
    }));
  }
  function saveKey(key) { return new Promise(r => chrome.storage.local.set({ rg_api_key: key }, r)); }
  function saveSettings() { chrome.storage.local.set({ rg_settings: state.settings }); }

  // ═══════════════════════════════════════════════════════════════════
  // MODELS
  // ═══════════════════════════════════════════════════════════════════
  async function fetchModels() {
    try {
      const res = await fetch(`${API_BASE}/models`);
      const data = await res.json();
      state.models = (data.data || [])
        .filter(m => m.pricing && m.pricing.prompt === '0' && m.pricing.completion === '0')
        .sort((a, b) => (a.name || '').localeCompare(b.name || ''));
      populateModelDropdown(dom.modelSelect);
      populateModelDropdown(dom.settingsModelSelect);
    } catch (err) {
      dom.modelSelect.innerHTML = '<option>⚠️ Failed to load</option>';
    }
  }

  function populateModelDropdown(select) {
    select.innerHTML = '';
    if (!state.models.length) { select.innerHTML = '<option value="">No free models</option>'; return; }
    state.models.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name || m.id;
      select.appendChild(opt);
    });
    const preferred = state.models.find(m => m.id.includes('llama')) || state.models[0];
    if (preferred) { select.value = preferred.id; state.model = preferred.id; }
  }

  async function validateKey(key) {
    try { return (await fetch(`${API_BASE}/models`, { headers: { 'Authorization': `Bearer ${key}` } })).ok; }
    catch { return false; }
  }

  // ═══════════════════════════════════════════════════════════════════
  // SETTINGS PANEL
  // ═══════════════════════════════════════════════════════════════════
  function openSettings() {
    dom.settingsKeyInput.value = state.apiKey;
    dom.settingsSessionMem.checked = state.settings.sessionMem;
    dom.settingsAutoCtx.checked = state.settings.autoCtx;
    dom.settingsCompact.checked = state.settings.compact;
    dom.settingsPanel.classList.add('open');
  }
  function closeSettings() {
    state.settings.sessionMem = dom.settingsSessionMem.checked;
    state.settings.autoCtx = dom.settingsAutoCtx.checked;
    state.settings.compact = dom.settingsCompact.checked;
    saveSettings();
    dom.settingsPanel.classList.remove('open');
  }

  // ═══════════════════════════════════════════════════════════════════
  // PAGE CONTEXT (reads current tab)
  // ═══════════════════════════════════════════════════════════════════
  async function grabPageContext() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) { console.warn('[RG Aide] No active tab found'); return ''; }

      // Can't inject into chrome:// or extension pages
      if (tab.url && (tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://'))) {
        console.warn('[RG Aide] Cannot read chrome:// pages');
        return '';
      }

      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          // Try to get the most meaningful content
          const selectors = ['article', 'main', '[role="main"]', '.content', '#content'];
          for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText.trim().length > 100) {
              return el.innerText.trim().substring(0, 6000);
            }
          }
          // Fallback: body text (skip scripts/styles)
          return document.body.innerText.substring(0, 6000);
        }
      });

      const text = results?.[0]?.result || '';
      console.log(`[RG Aide] Grabbed ${text.length} chars from page`);
      return text;
    } catch (err) {
      console.error('[RG Aide] Failed to grab page context:', err);
      return '';
    }
  }

  async function togglePageContext() {
    if (state.pageContextActive) {
      state.pageContextActive = false;
      state.pageContext = '';
      dom.pageCtxBtn.classList.remove('active');
    } else {
      dom.pageCtxBtn.classList.add('active');
      state.pageContext = await grabPageContext();
      state.pageContextActive = !!state.pageContext;
      if (!state.pageContext) {
        dom.pageCtxBtn.classList.remove('active');
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // FILE ATTACHMENTS
  // ═══════════════════════════════════════════════════════════════════
  function handleFiles(files) {
    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        state.attachments.push({ name: file.name, content: reader.result.substring(0, 5000) });
        renderAttachBar();
      };
      reader.readAsText(file);
    });
  }

  function renderAttachBar() {
    dom.attachBar.innerHTML = state.attachments.map((a, i) =>
      `<div class="attach-chip">📎 ${escHtml(a.name)} <span class="remove-chip" data-idx="${i}">✕</span></div>`
    ).join('');
    dom.attachBar.querySelectorAll('.remove-chip').forEach(el => {
      el.addEventListener('click', () => { state.attachments.splice(+el.dataset.idx, 1); renderAttachBar(); });
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  // SLASH COMMANDS
  // ═══════════════════════════════════════════════════════════════════
  const COMMANDS = {
    '/summarize': 'Summarize the current page content in bullet points.',
    '/extract': 'Extract all key data, links, headings, and important information from this page.',
    '/explain': 'Explain the content of this page in simple, easy-to-understand language.',
    '/help': null // handled specially
  };

  function processSlashCommand(text) {
    const cmd = text.trim().split(' ')[0].toLowerCase();
    if (cmd === '/help') {
      dom.welcomeState.style.display = 'none';
      dom.chatMessages.style.display = 'flex';
      renderMessage('ai', '**Available commands:**\n• `/summarize` — Summarize current page\n• `/extract` — Extract key data from page\n• `/explain` — Explain page simply\n• `/help` — Show this help');
      return true;
    }
    if (COMMANDS[cmd]) {
      // Auto-grab page context for slash commands
      (async () => {
        dom.pageCtxBtn.classList.add('active');
        state.pageContext = await grabPageContext();
        state.pageContextActive = !!state.pageContext;
        if (!state.pageContext) {
          dom.welcomeState.style.display = 'none';
          dom.chatMessages.style.display = 'flex';
          renderMessage('ai', '⚠️ Could not read the current page. Navigate to a regular webpage first.');
          dom.pageCtxBtn.classList.remove('active');
          return;
        }
        sendMessage(COMMANDS[cmd]);
      })();
      return true;
    }
    return false;
  }

  // ═══════════════════════════════════════════════════════════════════
  // CHAT ENGINE (send message + stream response)
  // ═══════════════════════════════════════════════════════════════════
  async function sendMessage(userText) {
    if (!userText.trim() || state.isStreaming) return;
    state.isStreaming = true;

    // Hide welcome, show messages
    dom.welcomeState.style.display = 'none';
    dom.chatMessages.style.display = 'flex';

    // If page context is active but not yet grabbed, grab it now
    if (state.pageContextActive && !state.pageContext) {
      state.pageContext = await grabPageContext();
    }

    // Render user message (show only what user typed)
    renderMessage('user', userText.trim(), { hasContext: state.pageContextActive && !!state.pageContext });

    // Build messages array for API
    // We inject a system message with page context so the AI KNOWS it has the content
    const messagesForApi = [];

    if (state.pageContextActive && state.pageContext) {
      messagesForApi.push({
        role: 'system',
        content: `You are a helpful assistant. The user is viewing a web page. Here is the full text content of that page:\n\n---PAGE START---\n${state.pageContext}\n---PAGE END---\n\nUse this page content to answer the user's questions. Always reference the page content directly. Do not ask the user to paste or share the page — you already have it.`
      });
    }

    // Add attachments as system context too
    if (state.attachments.length) {
      const attached = state.attachments.map(a => `[FILE: ${a.name}]\n${a.content}`).join('\n\n');
      messagesForApi.push({
        role: 'system',
        content: `The user has attached the following file(s):\n\n${attached}\n\nUse this content to answer their questions.`
      });
      state.attachments = [];
      renderAttachBar();
    }

    // Add conversation history
    messagesForApi.push(...state.sessionMemory);

    // Add current user message
    const userMsg = { role: 'user', content: userText.trim() };
    messagesForApi.push(userMsg);

    // Store in session memory (without system messages — those are rebuilt each time)
    state.sessionMemory.push(userMsg);
    updateMemoryBadge();

    // Reset input
    dom.chatInput.value = '';
    dom.chatInput.style.height = 'auto';
    dom.sendBtn.disabled = true;

    // Typing indicator
    const typingEl = showTyping();

    try {
      const response = await fetch(`${API_BASE}/chat/completions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${state.apiKey}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': chrome.runtime.getURL(''),
          'X-Title': 'RG Aide'
        },
        body: JSON.stringify({ model: state.model, messages: messagesForApi, stream: true })
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error?.message || `API error ${response.status}`);
      }

      const text = await streamResponse(response, typingEl);
      state.sessionMemory.push({ role: 'assistant', content: text });
      updateMemoryBadge();

    } catch (err) {
      typingEl.remove();
      renderMessage('ai', `❌ **Error:** ${err.message}`);
    } finally {
      state.isStreaming = false;
      // Reset page context after use (unless auto-ctx is on)
      if (!state.settings.autoCtx) {
        state.pageContextActive = false;
        state.pageContext = '';
        dom.pageCtxBtn.classList.remove('active');
      }
    }
  }

  async function streamResponse(response, typingEl) {
    typingEl.remove();
    const msgEl = createMsgElement('ai', '');
    dom.chatMessages.appendChild(msgEl);
    const contentEl = msgEl.querySelector('.msg-content');

    let fullText = '';
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') break;
        try {
          const token = JSON.parse(payload).choices?.[0]?.delta?.content || '';
          if (token) { fullText += token; contentEl.innerHTML = formatText(fullText); scrollToBottom(); }
        } catch {}
      }
    }
    contentEl.innerHTML = formatText(fullText);
    scrollToBottom();
    return fullText;
  }

  // ═══════════════════════════════════════════════════════════════════
  // UI RENDERING
  // ═══════════════════════════════════════════════════════════════════

  function createMsgElement(role, text, opts = {}) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    let contextBadge = '';
    if (opts.hasContext && role === 'user') {
      contextBadge = `<div class="msg-context-badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg> Page included</div>`;
    }

    // AI messages get action buttons (copy, regenerate)
    let actions = '';
    if (role === 'ai') {
      actions = `<div class="msg-actions">
        <button class="msg-action-btn copy-btn" title="Copy">📋 Copy</button>
        <button class="msg-action-btn regen-btn" title="Regenerate">🔄 Retry</button>
      </div>`;
    }

    div.innerHTML = `
      <div class="msg-avatar ${role === 'user' ? 'user' : 'ai'}">${role === 'user' ? '👤' : '🤖'}</div>
      <div class="msg-body">
        ${contextBadge}
        <div class="msg-content">${formatText(text)}</div>
        ${actions}
      </div>
    `;

    // Bind action buttons
    if (role === 'ai') {
      div.querySelector('.copy-btn').addEventListener('click', (e) => {
        const content = div.querySelector('.msg-content').innerText;
        navigator.clipboard.writeText(content);
        e.target.textContent = '✓ Copied';
        e.target.classList.add('copied');
        setTimeout(() => { e.target.textContent = '📋 Copy'; e.target.classList.remove('copied'); }, 1500);
      });
      div.querySelector('.regen-btn').addEventListener('click', () => {
        // Regenerate: remove last assistant msg from memory and resend
        if (state.sessionMemory.length >= 2) {
          state.sessionMemory.pop(); // remove assistant
          const lastUser = state.sessionMemory[state.sessionMemory.length - 1];
          div.remove(); // remove this message from DOM
          sendMessage(lastUser.content);
        }
      });
    }

    return div;
  }

  function renderMessage(role, text, opts = {}) {
    const el = createMsgElement(role, text, opts);
    dom.chatMessages.appendChild(el);
    scrollToBottom();
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'message ai';
    div.innerHTML = `<div class="msg-avatar ai">🤖</div><div class="msg-body"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
    dom.chatMessages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function scrollToBottom() { dom.chatArea.scrollTop = dom.chatArea.scrollHeight; }
  function updateMemoryBadge() { dom.memoryCount.textContent = state.sessionMemory.length; }

  function formatText(text) {
    if (!text) return '';
    return text
      .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }

  function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function autoResize() {
    dom.chatInput.style.height = 'auto';
    dom.chatInput.style.height = Math.min(dom.chatInput.scrollHeight, 100) + 'px';
  }

  function clearChat() {
    state.sessionMemory = [];
    state.pageContext = '';
    state.pageContextActive = false;
    state.attachments = [];
    dom.pageCtxBtn.classList.remove('active');
    dom.chatMessages.innerHTML = '';
    dom.chatMessages.style.display = 'none';
    dom.welcomeState.style.display = '';
    renderAttachBar();
    updateMemoryBadge();
  }

  function showSetupScreen() { dom.setupScreen.style.display = 'flex'; dom.chatScreen.style.display = 'none'; }
  function showChatScreen() { dom.setupScreen.style.display = 'none'; dom.chatScreen.style.display = 'flex'; }

  // ═══════════════════════════════════════════════════════════════════
  // EVENT LISTENERS
  // ═══════════════════════════════════════════════════════════════════

  // Setup
  dom.saveKeyBtn.addEventListener('click', async () => {
    const key = dom.apiKeyInput.value.trim();
    if (!key) { dom.keyError.textContent = 'Please paste your API key'; return; }
    if (!key.startsWith('sk-')) { dom.keyError.textContent = 'Key should start with "sk-"'; return; }
    dom.saveKeyBtn.textContent = 'Validating...'; dom.saveKeyBtn.disabled = true;
    const valid = await validateKey(key);
    if (valid) { state.apiKey = key; await saveKey(key); showChatScreen(); fetchModels(); }
    else { dom.keyError.textContent = 'Invalid key. Check and try again.'; }
    dom.saveKeyBtn.textContent = 'Save & Start'; dom.saveKeyBtn.disabled = false;
  });

  // Send
  dom.sendBtn.addEventListener('click', () => {
    const text = dom.chatInput.value.trim();
    if (processSlashCommand(text)) { dom.chatInput.value = ''; return; }
    sendMessage(text);
  });
  dom.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const text = dom.chatInput.value.trim();
      if (processSlashCommand(text)) { dom.chatInput.value = ''; return; }
      sendMessage(text);
    }
  });
  dom.chatInput.addEventListener('input', () => { dom.sendBtn.disabled = !dom.chatInput.value.trim(); autoResize(); });

  // Model change
  dom.modelSelect.addEventListener('change', () => { state.model = dom.modelSelect.value; });
  dom.settingsModelSelect?.addEventListener('change', () => {
    state.model = dom.settingsModelSelect.value;
    dom.modelSelect.value = state.model;
  });

  // Page context
  dom.pageCtxBtn.addEventListener('click', togglePageContext);

  // Attachments
  dom.attachBtn.addEventListener('click', () => dom.fileInput.click());
  dom.fileInput.addEventListener('change', (e) => { handleFiles(e.target.files); dom.fileInput.value = ''; });

  // New chat
  dom.newChatBtn.addEventListener('click', clearChat);

  // Settings
  dom.settingsBtn.addEventListener('click', openSettings);
  dom.settingsCloseBtn.addEventListener('click', closeSettings);
  dom.settingsBackdrop.addEventListener('click', closeSettings);
  dom.settingsKeySave.addEventListener('click', async () => {
    const key = dom.settingsKeyInput.value.trim();
    if (!key) { dom.settingsKeyStatus.textContent = '⚠️ Enter a key'; dom.settingsKeyStatus.className = 's-status err'; return; }
    const valid = await validateKey(key);
    if (valid) {
      state.apiKey = key; await saveKey(key);
      dom.settingsKeyStatus.textContent = '✓ Saved'; dom.settingsKeyStatus.className = 's-status ok';
    } else {
      dom.settingsKeyStatus.textContent = '✗ Invalid key'; dom.settingsKeyStatus.className = 's-status err';
    }
    setTimeout(() => { dom.settingsKeyStatus.textContent = ''; }, 2500);
  });

  // Suggested prompt chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', async () => {
      const prompt = chip.dataset.prompt;
      // All chips that mention "page" auto-include page context
      if (prompt.toLowerCase().includes('page')) {
        dom.pageCtxBtn.classList.add('active');
        state.pageContext = await grabPageContext();
        state.pageContextActive = !!state.pageContext;
        if (!state.pageContext) {
          renderMessage('ai', '⚠️ Could not read the current page. Make sure you\'re on a regular webpage (not a Chrome settings page).');
          dom.pageCtxBtn.classList.remove('active');
          return;
        }
      }
      sendMessage(prompt);
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BOOT
  // ═══════════════════════════════════════════════════════════════════
  async function boot() {
    const saved = await loadKey();
    if (saved) { state.apiKey = saved; showChatScreen(); fetchModels(); }
    else { showSetupScreen(); }
  }
  boot();

} // end main()

// ─── SECURITY ──────────────────────────────────────────────────────
(function() {
  'use strict';
  window.addEventListener('beforeunload', () => {
    if (window.__state) { window.__state.sessionMemory = []; window.__state.apiKey = ''; }
  });
})();
