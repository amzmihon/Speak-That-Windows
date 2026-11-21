chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "toggle-bionic-reading",
    title: "Toggle Bionic Reading",
    contexts: ["page", "selection"]
  });
});

// Context Menu: Toggle Bionic Reading
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "toggle-bionic-reading") {
    chrome.storage.sync.get({ enabled: true }, (data) => {
      const nextState = !data.enabled;
      chrome.storage.sync.set({ enabled: nextState }, () => {
        chrome.storage.sync.get(null, (allSettings) => {
          broadcastSettings(allSettings);
        });
      });
    });
  }
});

// Keyboard Commands (Alt+B to toggle Bionic, Alt+R to toggle Reader)
chrome.commands.onCommand.addListener((command) => {
  if (command === "toggle-bionic") {
    chrome.storage.sync.get({ enabled: true }, (data) => {
      const nextState = !data.enabled;
      chrome.storage.sync.set({ enabled: nextState }, () => {
        chrome.storage.sync.get(null, (allSettings) => {
          broadcastSettings(allSettings);
        });
      });
    });
  } else if (command === "toggle-reader") {
    chrome.storage.sync.get({ readerModeEnabled: false }, (data) => {
      const nextState = !data.readerModeEnabled;
      chrome.storage.sync.set({ readerModeEnabled: nextState }, () => {
        chrome.storage.sync.get(null, (allSettings) => {
          broadcastSettings(allSettings);
        });
      });
    });
  }
});

function broadcastSettings(settings) {
  chrome.tabs.query({}, (tabs) => {
    tabs.forEach((tab) => {
      if (tab.id) {
        chrome.tabs.sendMessage(tab.id, { action: "settings_updated", settings }).catch(() => {});
      }
    });
  });
}
