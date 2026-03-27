const input = document.getElementById("apiUrl");
const saveBtn = document.getElementById("saveBtn");
const savedMsg = document.getElementById("savedMsg");

// Load saved URL
chrome.storage.sync.get({ apiUrl: "http://localhost:8000" }, (data) => {
  input.value = data.apiUrl;
});

// Save
saveBtn.addEventListener("click", () => {
  const url = input.value.trim().replace(/\/+$/, "");
  chrome.storage.sync.set({ apiUrl: url }, () => {
    savedMsg.style.display = "inline";
    setTimeout(() => { savedMsg.style.display = "none"; }, 2000);
  });
});
