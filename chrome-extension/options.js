/**
 * RG Aide — Options Page Logic
 * Copyright (c) 2026 Rahul Goel. MIT License.
 */
'use strict';

const keyInput = document.getElementById('apiKey');
const saveBtn = document.getElementById('saveBtn');
const clearBtn = document.getElementById('clearBtn');
const status = document.getElementById('status');

// Load saved key on open
chrome.storage.local.get(['rg_api_key'], (result) => {
  if (result.rg_api_key) {
    keyInput.value = result.rg_api_key;
  }
});

// Save key
saveBtn.addEventListener('click', () => {
  const key = keyInput.value.trim();
  if (!key) {
    showStatus('⚠️ Enter a key first', '#ff9800');
    return;
  }
  chrome.storage.local.set({ rg_api_key: key }, () => {
    showStatus('✓ Saved!', '#4caf50');
  });
});

// Clear key
clearBtn.addEventListener('click', () => {
  chrome.storage.local.remove('rg_api_key', () => {
    keyInput.value = '';
    showStatus('✓ Key cleared', '#4caf50');
  });
});

// Flash status message
function showStatus(msg, color) {
  status.textContent = msg;
  status.style.color = color;
  setTimeout(() => { status.textContent = ''; }, 2500);
}
