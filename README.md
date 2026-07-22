# RG Aide — Free AI Browser Sidebar

<p align="center">
  <img src="chrome-extension/icon128.png" alt="RG Aide" width="80">
</p>

<p align="center">
  <strong>Your personal AI assistant that lives in Chrome's sidebar.</strong><br>
  Free models. Private memory. Reads any page. Zero setup hassle.
</p>

<p align="center">
  <a href="#-quickest-install-no-git-needed">Download & Install</a> •
  <a href="#-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-commands">Commands</a> •
  <a href="#-privacy">Privacy</a>
</p>

---

## ⚡ Quickest Install (No Git Needed)

**Total time: 2 minutes.**

### Step 1 — Download

Click the green **Code** button on this repo → **Download ZIP** → Extract anywhere on your computer.

Or if you just want the extension folder:
1. Go to [this repo's chrome-extension folder](./chrome-extension/)
2. Download all files into a folder on your computer

### Step 2 — Load in Chrome

1. Open Chrome → type `chrome://extensions/` in the address bar
2. Turn ON **Developer mode** (toggle in top-right corner)
3. Click **"Load unpacked"**
4. Select the `chrome-extension/` folder you downloaded
5. ✅ You'll see **RG Aide** appear in your extensions

### Step 3 — Get a Free API Key

1. Go to → [openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign up (free, 30 seconds)
3. Click **"Create Key"**
4. Copy the key (starts with `sk-or-...`)

### Step 4 — Start Using

1. Click the **RG Aide icon** in Chrome's toolbar
2. Sidebar opens → **paste your API key**
3. Click **"Save & Start"**
4. You're in! Start chatting 🎉

---

## 🔧 Install via Git Clone (For Developers)

```bash
git clone https://github.com/rahgoel2510/resumatch-ai.git
cd resumatch-ai/chrome-extension
```

Then follow Steps 2–4 above.

### Optional: Compile SCSS (if editing styles)

```bash
cd chrome-extension
./build.sh          # Compile once
./build.sh watch    # Auto-compile on save
./build.sh prod     # Production: obfuscate + package
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 💬 **AI Chat** | Conversation with free AI models, streamed token-by-token |
| 📄 **Auto Page Context** | Automatically reads the current page and sends it with your question |
| 🗂️ **Multi-Tab Context** | Select multiple open tabs to include as context (compare, cross-reference) |
| 📎 **File Attachments** | Drop text files (.txt, .md, .csv, .json) into the chat |
| ⚡ **Suggested Prompts** | One-click: Summarize, Extract Key Points, Explain |
| ⌨️ **Slash Commands** | `/summarize`, `/extract`, `/explain`, `/help` |
| 📋 **Copy & Regenerate** | Clean icon buttons on every AI response |
| 🕐 **Chat History** | All conversations saved locally, browse and reload anytime |
| ⚙️ **Smart Settings** | Model browser, API key, privacy toggles, personalization |
| 🎨 **Personalization** | Set your name + custom extension name |
| 🔵 **LLM Status Dot** | Animated indicator — blue pulse when AI is thinking |
| 🔒 **Private by Default** | Session memory in RAM, auto-cleared on close |

---

## 🖥️ How It Works

```
You open any webpage
       ↓
Click RG Aide icon → sidebar opens
       ↓
Type a question (or click a suggested prompt)
       ↓
Extension auto-reads the page content
       ↓
Sends: [page context] + [your question] → AI model
       ↓
Streamed response appears token-by-token
       ↓
Memory cleared when sidebar closes (private)
```

### Page Context (Automatic)

Every time you send a message, the extension **automatically reads** the current page and includes it. You don't need to click anything — just ask.

If you want to include **additional tabs**:
1. Click the 🗂️ purple icon
2. Select tabs from the picker
3. Ask your question — AI gets content from all selected tabs

### Multi-Source Example

Open 3 job postings in different tabs → click 🗂️ → select all 3 → ask:
> "Compare these three positions and tell me which best matches a senior backend engineer"

The AI gets full content from all 3 pages and cross-references them.

---

## ⌨️ Commands

Type these in the chat input:

| Command | What it does |
|---------|-------------|
| `/summarize` | Summarize the current page in bullet points |
| `/extract` | Extract key data, links, headings from the page |
| `/explain` | Explain the page content in simple language |
| `/help` | Show available commands |

---

## ⚙️ Settings

Click the **⚙️ gear icon** in the topbar to open settings:

| Section | Options |
|---------|---------|
| **AI Model** | Browse & select from free models (with context size info) |
| **API Key** | Save/change your key with live validation |
| **Privacy** | Session-only memory toggle, auto page context toggle |
| **Appearance** | Compact mode |
| **Personalization** | Your name, custom extension name |
| **About** | Version, license info |

---

## 🔒 Privacy

| What | Where it goes |
|------|---------------|
| API Key | `chrome.storage.local` (your machine only) |
| Conversations | JavaScript array in RAM (never written to disk) |
| Chat History | `chrome.storage.local` (on-device only) |
| Page Content | Grabbed, sent to AI model, then discarded |
| Files | Read into memory, sent to AI, then discarded |

**Nothing is ever sent to any server except the AI inference provider (for generating responses).**

When you close the sidebar or click "New Chat", the active session memory is wiped from RAM.

---

## 📁 File Structure

```
chrome-extension/
├── manifest.json       ← Extension config (4 permissions)
├── background.js       ← Opens sidebar on icon click (7 lines)
├── sidepanel.html      ← UI (setup + chat screens)
├── aide.js             ← All logic (AI, chat, memory, context)
├── aide.scss           ← Styles source (edit this)
├── aide.css            ← Compiled styles (auto-generated)
├── options.html/js/css ← Settings page (API key shortcut)
├── build.sh            ← SCSS compiler + production build
├── icon*.png           ← Extension icons
├── LICENSE             ← MIT License
├── INSTALL.md          ← Quick install guide
└── README.md           ← This file
```

---

## 🔄 Updating

### Downloaded as ZIP:
1. Download the latest ZIP
2. Replace the `chrome-extension/` folder
3. Go to `chrome://extensions/` → click the ↻ refresh button on RG Aide

### Cloned via Git:
```bash
git pull
```
Then refresh in `chrome://extensions/`.

---

## 🤔 FAQ

**Q: Is it really free?**
Yes. The extension uses free AI models from the provider. No credit card needed.

**Q: Which models are available?**
All free models from the provider are shown in Settings → AI Model. Includes Llama, Gemma, Phi, and more.

**Q: Can I use it on any website?**
Yes — any regular webpage. It cannot read `chrome://` system pages or other extensions.

**Q: What if I close the sidebar mid-conversation?**
Your conversation is saved to history (🕐 icon). Reopen and load it anytime.

**Q: Does it work offline?**
No — it needs internet to reach the AI model. But nothing is stored remotely.

**Q: How do I change my API key?**
Settings (⚙️) → API Key section → paste new key → Save.

**Q: Can I use this on Edge/Brave?**
Yes — any Chromium-based browser supports this extension via Developer mode.

---

## 🛡️ Security

- **No eval()** — blocked at runtime
- **Session memory wiped** on sidebar close (`beforeunload`)
- **Production build** available: `./build.sh prod` — obfuscates all code (unreadable output)
- **MIT Licensed** — full source visible, auditable

---

## 📝 License

MIT License — Copyright (c) 2026 Rahul Goel.

Free to use, modify, and distribute. See [LICENSE](chrome-extension/LICENSE).
