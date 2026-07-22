# Install RG Aide

**Time needed: 2 minutes. No coding required.**

---

## Features

- **📄 Page Context** — Click the page icon to include current tab content with your message
- **💡 Suggested Prompts** — Quick-action chips: Summarize, Key Points, Extract, Explain
- **📋 Copy / 🔄 Retry** — Action buttons on every AI response
- **📎 File Attachments** — Drop text files into the chat for analysis
- **⌨️ Slash Commands** — `/summarize`, `/extract`, `/explain`, `/help`
- **⚙️ Professional Settings** — Slide-over panel with model, key, privacy, and appearance controls
- **💭 Session Memory** — Private, RAM-only, cleared on close

---

## Step 1: Download the Extension

Download or clone this folder to your computer:

```
chrome-extension/
```

That's the entire extension. No build step, no npm, no compilation.

---

## Step 2: Load in Chrome

1. Open Chrome and go to: `chrome://extensions/`
2. Turn ON **"Developer mode"** (top-right toggle)
3. Click **"Load unpacked"**
4. Select the `chrome-extension/` folder
5. Done! You'll see the RG Aide icon in your toolbar

---

## Step 3: Get Your Free API Key

1. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign up (free — takes 30 seconds)
3. Click **"Create Key"**
4. Copy the key (starts with `sk-or-...`)

---

## Step 4: Start Using

1. Click the RG Aide icon in Chrome toolbar
2. The sidebar opens → paste your API key
3. Click "Save & Start Chatting"
4. Pick any free model from the dropdown
5. Start chatting! 🎉

---

## That's It!

No backend server to run. No Docker. No environment variables.
Just a Chrome extension + a free API key.

---

## FAQ

**Q: Is it really free?**
Yes. The API provider offers many models at zero cost. The extension only shows free models.

**Q: Where is my API key stored?**
In Chrome's local storage (on your computer only). It's only sent to the AI inference provider.

**Q: Is my conversation private?**
Yes. Conversations exist only in browser memory. When you close the sidebar or click "New Chat", the memory is wiped. Nothing is saved to disk.

**Q: How do I change my API key?**
Click the ⚙️ settings gear icon in the sidebar, or right-click the extension → Options.

**Q: How do I update the extension?**
Pull the latest code, then go to `chrome://extensions/` and click the refresh ↻ button.

---

## File Structure (for developers)

```
chrome-extension/
├── manifest.json      ← Chrome extension config (2 permissions only)
├── background.js      ← Opens side panel on icon click
├── sidepanel.html     ← The UI (2 screens: setup + chat)
├── aide.scss          ← Styles SOURCE (edit this)
├── aide.css           ← Compiled output (don't edit directly)
├── aide.js            ← All logic (API, chat, memory)
├── options.html       ← Settings page
├── options.scss       ← Settings styles SOURCE
├── options.css        ← Compiled output
├── options.js         ← Settings logic
├── build.sh           ← SCSS compiler (./build.sh or ./build.sh watch)
└── icon*.png          ← Extension icons
```

### Editing Styles

```bash
./build.sh          # Compile once
./build.sh watch    # Auto-compile on save
./build.sh prod     # Production: obfuscate + package
```

---

## License

MIT License — Copyright (c) 2026 Rahul Goel.
See LICENSE file for details.
