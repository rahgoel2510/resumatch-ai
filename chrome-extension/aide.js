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
    settings: { sessionMem: true, autoCtx: false, compact: false, userName: '', appName: '' }
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

    // Render model cards in settings browser
    renderModelBrowser();
  }

  function renderModelBrowser() {
    const browser = document.getElementById('modelBrowser');
    if (!browser) return;
    browser.innerHTML = '';
    state.models.slice(0, 15).forEach(m => {
      const card = document.createElement('div');
      card.className = `model-card${m.id === state.model ? ' selected' : ''}`;
      const ctx = m.context_length ? `${Math.round(m.context_length / 1000)}k ctx` : '';
      card.innerHTML = `
        <div class="model-card-info">
          <div class="model-card-name">${escHtml(m.name || m.id)}</div>
          <div class="model-card-meta">${ctx}</div>
        </div>
        <span class="model-card-badge free">FREE</span>
      `;
      card.addEventListener('click', () => {
        state.model = m.id;
        dom.modelSelect.value = m.id;
        dom.settingsModelSelect.value = m.id;
        browser.querySelectorAll('.model-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
      });
      browser.appendChild(card);
    });
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
    document.getElementById('settingsUserName').value = state.settings.userName || '';
    document.getElementById('settingsAppName').value = state.settings.appName || '';
    dom.settingsPanel.classList.add('open');
  }
  function closeSettings() {
    state.settings.sessionMem = dom.settingsSessionMem.checked;
    state.settings.autoCtx = dom.settingsAutoCtx.checked;
    state.settings.compact = dom.settingsCompact.checked;
    state.settings.userName = document.getElementById('settingsUserName').value.trim();
    state.settings.appName = document.getElementById('settingsAppName').value.trim();
    saveSettings();
    applyPersonalization();
    dom.settingsPanel.classList.remove('open');
  }

  /**
   * Apply user's custom name and app name to the UI.
   * Updates: topbar title, welcome screen title, document title, about section.
   */
  function applyPersonalization() {
    const appName = state.settings.appName || 'RG Aide';
    const userName = state.settings.userName || '';

    // Topbar title
    const topTitle = document.querySelector('.topbar-title');
    if (topTitle) topTitle.textContent = appName;

    // Welcome title
    const welcomeTitle = document.querySelector('.welcome-title');
    if (welcomeTitle) {
      welcomeTitle.textContent = userName ? `Hi ${userName}! Let's go.` : 'All set. Let\'s go.';
    }

    // Document title
    document.title = appName;

    // About section
    const aboutEl = document.getElementById('aboutAppName');
    if (aboutEl) aboutEl.textContent = `${appName} v1.0.0`;
  }

  // ═══════════════════════════════════════════════════════════════════
  // CHAT HISTORY (persisted in chrome.storage.local)
  // ═══════════════════════════════════════════════════════════════════

  /**
   * Save current session to history.
   * Called when: user clicks "New Chat", or manually.
   * Each session: { id, timestamp, model, messages[], preview }
   */
  async function saveSessionToHistory() {
    if (state.sessionMemory.length === 0) return; // nothing to save

    const session = {
      id: Date.now(),
      timestamp: Date.now(),
      model: state.model,
      messages: state.sessionMemory.slice(), // copy
      preview: state.sessionMemory.find(m => m.role === 'user')?.content.substring(0, 80) || 'Chat session'
    };

    const stored = await getHistory();
    stored.unshift(session);
    // Keep max 50 sessions
    if (stored.length > 50) stored.length = 50;
    await chrome.storage.local.set({ rg_history: stored });
  }

  function getHistory() {
    return new Promise(resolve => {
      chrome.storage.local.get(['rg_history'], (d) => resolve(d.rg_history || []));
    });
  }

  async function deleteSession(id) {
    const stored = await getHistory();
    const filtered = stored.filter(s => s.id !== id);
    await chrome.storage.local.set({ rg_history: filtered });
    renderHistoryPanel();
  }

  async function loadSession(id) {
    const stored = await getHistory();
    const session = stored.find(s => s.id === id);
    if (!session) return;

    // Load into current chat
    state.sessionMemory = session.messages.slice();
    dom.welcomeState.style.display = 'none';
    dom.chatMessages.style.display = 'flex';
    dom.chatMessages.innerHTML = '';

    // Render all messages
    session.messages.forEach(msg => {
      renderMessage(msg.role === 'assistant' ? 'ai' : 'user', msg.content);
    });

    updateMemoryBadge();
    closeHistory();
  }

  function openHistory() {
    document.getElementById('historyPanel').classList.add('open');
    renderHistoryPanel();
  }

  function closeHistory() {
    document.getElementById('historyPanel').classList.remove('open');
  }

  async function renderHistoryPanel() {
    const list = document.getElementById('historyList');
    const empty = document.getElementById('historyEmpty');
    const stored = await getHistory();

    if (stored.length === 0) {
      list.innerHTML = '';
      empty.style.display = 'block';
      return;
    }

    empty.style.display = 'none';
    list.innerHTML = stored.map(s => {
      const date = new Date(s.timestamp);
      const timeStr = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' · ' +
                      date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
      const msgCount = s.messages.length;
      return `
        <div class="history-item" data-id="${s.id}">
          <div class="history-item-content">
            <div class="history-item-preview">${escHtml(s.preview)}</div>
            <div class="history-item-meta">${timeStr} · ${msgCount} messages</div>
          </div>
          <button class="history-item-delete" data-id="${s.id}" title="Delete">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          </button>
        </div>`;
    }).join('');

    // Bind click events
    list.querySelectorAll('.history-item-content').forEach(el => {
      el.addEventListener('click', () => loadSession(+el.parentElement.dataset.id));
    });
    list.querySelectorAll('.history-item-delete').forEach(el => {
      el.addEventListener('click', (e) => { e.stopPropagation(); deleteSession(+el.dataset.id); });
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  // PAGE CONTEXT (reads current tab)
  // ═══════════════════════════════════════════════════════════════════
  async function grabPageContext() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) { console.warn('[RG Aide] No active tab found'); return ''; }
      if (tab.url && (tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://'))) {
        console.warn('[RG Aide] Cannot read chrome:// pages');
        return '';
      }
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          const selectors = ['article', 'main', '[role="main"]', '.content', '#content'];
          for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText.trim().length > 100) return el.innerText.trim().substring(0, 6000);
          }
          return document.body.innerText.substring(0, 6000);
        }
      });
      const text = results?.[0]?.result || '';
      console.log(`[RG Aide] Grabbed ${text.length} chars from page`);
      return text;
    } catch (err) { console.error('[RG Aide] Page context error:', err); return ''; }
  }

  /** Grab content from a specific tab by ID */
  async function grabTabContent(tabId) {
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
          const selectors = ['article', 'main', '[role="main"]', '.content', '#content'];
          for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText.trim().length > 100) return el.innerText.trim().substring(0, 4000);
          }
          return document.body.innerText.substring(0, 4000);
        }
      });
      return results?.[0]?.result || '';
    } catch { return ''; }
  }

  // Context sources: [{type: 'page'|'tab', title, content}]
  let contextSources = [];

  function renderContextBar() {
    const bar = dom.contextBar;
    bar.innerHTML = contextSources.map((src, i) =>
      `<div class="context-chip">
        <span class="chip-text">${src.type === 'page' ? '📄' : '🗂️'} ${escHtml(src.title)}</span>
        <span class="chip-remove" data-idx="${i}">✕</span>
      </div>`
    ).join('');
    bar.querySelectorAll('.chip-remove').forEach(el => {
      el.addEventListener('click', () => { contextSources.splice(+el.dataset.idx, 1); renderContextBar(); });
    });
    updateMemoryBadge();
  }

  async function togglePageContext() {
    if (state.pageContextActive) {
      state.pageContextActive = false;
      state.pageContext = '';
      dom.pageCtxBtn.classList.remove('active');
      // Remove page source from contextSources
      contextSources = contextSources.filter(s => s.type !== 'page');
      renderContextBar();
    } else {
      dom.pageCtxBtn.classList.add('active');
      const text = await grabPageContext();
      if (text) {
        state.pageContext = text;
        state.pageContextActive = true;
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        contextSources.push({ type: 'page', title: tab?.title || 'Current page', content: text });
        renderContextBar();
      } else {
        dom.pageCtxBtn.classList.remove('active');
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // MULTI-TAB CONTEXT PICKER
  // ═══════════════════════════════════════════════════════════════════
  const tabPickerDom = {
    picker: document.getElementById('tabPicker'),
    list: document.getElementById('tabPickerList'),
    close: document.getElementById('tabPickerClose'),
    confirm: document.getElementById('tabPickerConfirm'),
    count: document.getElementById('tabPickerCount'),
    btn: document.getElementById('multiTabBtn'),
    contextBar: document.getElementById('contextBar'),
  };
  // Also add contextBar to dom
  dom.contextBar = document.getElementById('contextBar');

  async function openTabPicker() {
    tabPickerDom.picker.classList.add('open');
    tabPickerDom.list.innerHTML = '<div style="padding:12px;color:#6b7394;font-size:12px">Loading tabs...</div>';

    const tabs = await chrome.tabs.query({ currentWindow: true });
    tabPickerDom.list.innerHTML = '';

    tabs.forEach(tab => {
      // Skip chrome:// and extension pages
      if (tab.url && (tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://') || tab.url.startsWith('about:'))) return;

      const item = document.createElement('div');
      item.className = 'tab-picker-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.dataset.tabId = tab.id;
      checkbox.dataset.tabTitle = tab.title || 'Untitled';

      const info = document.createElement('div');
      info.innerHTML = `
        <div class="tab-picker-title">${escHtml(tab.title || 'Untitled')}</div>
        <div class="tab-picker-url">${escHtml((tab.url || '').substring(0, 60))}</div>
      `;

      item.appendChild(checkbox);
      item.appendChild(info);

      // Click anywhere on item toggles checkbox
      item.addEventListener('click', (e) => {
        if (e.target !== checkbox) {
          checkbox.checked = !checkbox.checked;
        }
        item.classList.toggle('selected', checkbox.checked);
        updateTabPickerCount();
      });

      tabPickerDom.list.appendChild(item);
    });

    updateTabPickerCount();
  }

  function updateTabPickerCount() {
    const checked = tabPickerDom.list.querySelectorAll('input[type="checkbox"]:checked');
    const n = checked.length;
    tabPickerDom.count.textContent = `${n} selected`;
    tabPickerDom.confirm.disabled = n === 0;
  }

  async function confirmTabPicker() {
    const checked = tabPickerDom.list.querySelectorAll('input[type="checkbox"]:checked');
    tabPickerDom.picker.classList.remove('open');

    for (const cb of checked) {
      const tabId = parseInt(cb.dataset.tabId);
      const title = cb.dataset.tabTitle || 'Tab';
      const content = await grabTabContent(tabId);
      if (content) {
        contextSources.push({ type: 'tab', title, content });
      }
    }
    renderContextBar();
    tabPickerDom.btn.classList.toggle('active', contextSources.some(s => s.type === 'tab'));
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

    // Show LLM thinking animation
    const llmStatus = document.getElementById('llmStatus');
    if (llmStatus) { llmStatus.classList.add('thinking'); llmStatus.title = 'AI Thinking...'; }

    // Hide welcome, show messages
    dom.welcomeState.style.display = 'none';
    dom.chatMessages.style.display = 'flex';

    // If page context is active but not yet grabbed, grab it now
    if (state.pageContextActive && !state.pageContext) {
      state.pageContext = await grabPageContext();
    }

    // Render user message
    const hasCtx = contextSources.length > 0 || (state.attachments.length > 0);
    renderMessage('user', userText.trim(), { hasContext: hasCtx });

    // Build messages array for API
    const messagesForApi = [];

    // Inject ALL context sources as system message
    if (contextSources.length > 0) {
      const combined = contextSources.map((src, i) =>
        `--- SOURCE ${i + 1}: ${src.title} ---\n${src.content}\n--- END SOURCE ${i + 1} ---`
      ).join('\n\n');

      messagesForApi.push({
        role: 'system',
        content: `You are a helpful assistant. The user has provided the following web page content(s) as context:\n\n${combined}\n\nUse this content to answer the user's questions directly. Do NOT ask the user to paste or share the content — you already have it. Reference specific parts when relevant.`
      });
    }

    // Add attachments as system context
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
      // Stop LLM thinking animation
      const llmStatus = document.getElementById('llmStatus');
      if (llmStatus) { llmStatus.classList.remove('thinking'); llmStatus.title = 'AI Ready'; }
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
  function updateMemoryBadge() {
    const tabLabel = document.getElementById('tabContextLabel');
    if (tabLabel) {
      const n = contextSources.length;
      tabLabel.textContent = n > 0 ? `${n} source${n > 1 ? 's' : ''} attached` : 'No tabs selected';
    }
  }

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
    // Save current session before clearing
    saveSessionToHistory();

    state.sessionMemory = [];
    state.pageContext = '';
    state.pageContextActive = false;
    state.attachments = [];
    contextSources = [];
    dom.pageCtxBtn.classList.remove('active');
    tabPickerDom.btn.classList.remove('active');
    dom.chatMessages.innerHTML = '';
    dom.chatMessages.style.display = 'none';
    dom.welcomeState.style.display = '';
    renderAttachBar();
    renderContextBar();
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

  // Multi-tab picker
  tabPickerDom.btn.addEventListener('click', openTabPicker);
  tabPickerDom.close.addEventListener('click', () => tabPickerDom.picker.classList.remove('open'));
  tabPickerDom.confirm.addEventListener('click', confirmTabPicker);

  // Attachments
  dom.attachBtn.addEventListener('click', () => dom.fileInput.click());
  dom.fileInput.addEventListener('change', (e) => { handleFiles(e.target.files); dom.fileInput.value = ''; });

  // New chat
  dom.newChatBtn.addEventListener('click', clearChat);

  // Settings
  dom.settingsBtn.addEventListener('click', openSettings);
  dom.settingsCloseBtn.addEventListener('click', closeSettings);
  dom.settingsBackdrop.addEventListener('click', closeSettings);

  // History
  document.getElementById('historyBtn').addEventListener('click', openHistory);
  document.getElementById('historyCloseBtn').addEventListener('click', closeHistory);
  document.getElementById('historyBackdrop').addEventListener('click', closeHistory);
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
    applyPersonalization();
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
