const DEFAULT_SETTINGS = {
  enabled: true,
  fixationRatio: 0.4,
  bionicBoldness: 1.0,
  blacklist: [],
  allowedScripts: ['Latin'],
  primaryMode: 'light',
  focusEnabled: false,
  bwEnabled: false,
  hcEnabled: false,
  nightLightEnabled: false,
  adhdEnabled: false,
  readerModeEnabled: false
};

let currentSettings = { ...DEFAULT_SETTINGS };

const enableToggle = document.getElementById('enable-toggle');
const fixationSlider = document.getElementById('fixation-slider');
const fixationValue = document.getElementById('fixation-value');
const boldnessSlider = document.getElementById('boldness-slider');
const boldnessValue = document.getElementById('boldness-value');
const blacklistBtn = document.getElementById('blacklist-btn');
const currentDomainEl = document.getElementById('current-domain');

const cyrillicToggle = document.getElementById('cyrillic-toggle');
const greekToggle = document.getElementById('greek-toggle');
const experimentalToggle = document.getElementById('experimental-toggle');

// Primary Mode Radio Buttons
const modeLight = document.getElementById('mode-light');
const modeGray = document.getElementById('mode-gray');
const modeBlack = document.getElementById('mode-black');

// Additive Feature Checkboxes
const focusToggle = document.getElementById('focus-toggle');
const bwToggle = document.getElementById('bw-toggle');
const hcToggle = document.getElementById('hc-toggle');
const nightLightToggle = document.getElementById('nightlight-toggle');
const adhdToggle = document.getElementById('adhd-toggle');

// Reader Mode Toggle
const readerToggle = document.getElementById('reader-toggle');

let currentHostname = '';
let saveTimeout = null;

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url) {
    try {
      const url = new URL(tab.url);
      currentHostname = url.hostname;
      if (currentDomainEl) currentDomainEl.textContent = currentHostname;

      chrome.tabs.sendMessage(tab.id, { action: "ping" }).catch(() => {
        if (currentDomainEl) {
          currentDomainEl.textContent = "⚠️ Extension disabled on this page";
          currentDomainEl.style.color = "#d32f2f";
        }
        disableAllInputs();
      });
    } catch (e) {
      if (currentDomainEl) currentDomainEl.textContent = "Invalid URL";
      if (blacklistBtn) blacklistBtn.disabled = true;
    }
  } else {
    if (currentDomainEl) currentDomainEl.textContent = "Cannot access tab";
    if (blacklistBtn) blacklistBtn.disabled = true;
  }

  chrome.storage.sync.get(DEFAULT_SETTINGS, (settings) => {
    currentSettings = settings;
    if (enableToggle) enableToggle.checked = settings.enabled;
    if (fixationSlider) fixationSlider.value = settings.fixationRatio * 100;
    if (fixationValue) fixationValue.textContent = `${settings.fixationRatio * 100}%`;
    if (boldnessSlider) boldnessSlider.value = settings.bionicBoldness;
    if (boldnessValue) boldnessValue.textContent = `${settings.bionicBoldness}x`;

    const scripts = settings.allowedScripts || ['Latin'];
    if (cyrillicToggle) cyrillicToggle.checked = scripts.includes('Cyrillic');
    if (greekToggle) greekToggle.checked = scripts.includes('Greek');
    if (experimentalToggle) experimentalToggle.checked = scripts.includes('Experimental (All other scripts)');

    // Hydrate primary mode radio buttons
    const mode = settings.primaryMode || 'light';
    if (mode === 'gray' && modeGray) modeGray.checked = true;
    else if (mode === 'black' && modeBlack) modeBlack.checked = true;
    else if (modeLight) modeLight.checked = true;

    // Hydrate additive feature checkboxes
    if (focusToggle) focusToggle.checked = settings.focusEnabled || false;
    if (bwToggle) bwToggle.checked = settings.bwEnabled || false;
    if (hcToggle) hcToggle.checked = settings.hcEnabled || false;
    if (nightLightToggle) nightLightToggle.checked = settings.nightLightEnabled || false;
    if (adhdToggle) adhdToggle.checked = settings.adhdEnabled || false;
    if (readerToggle) readerToggle.checked = settings.readerModeEnabled || false;

    updateBlacklistBtnUI(settings.blacklist.includes(currentHostname));
  });

  if (enableToggle) enableToggle.addEventListener('change', (e) => {
    currentSettings.enabled = e.target.checked;
    queueSaveSettings();
  });

  if (fixationSlider) fixationSlider.addEventListener('input', (e) => {
    if (fixationValue) fixationValue.textContent = `${e.target.value}%`;
    currentSettings.fixationRatio = parseInt(e.target.value) / 100;
    queueSaveSettings();
  });

  if (boldnessSlider) boldnessSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value).toFixed(1);
    if (boldnessValue) boldnessValue.textContent = `${val}x`;
    currentSettings.bionicBoldness = parseFloat(val);
    queueSaveSettings();
  });

  function toggleScript(scriptName, isEnabled) {
    if (!currentSettings.allowedScripts) currentSettings.allowedScripts = ['Latin'];
    if (isEnabled) {
      if (!currentSettings.allowedScripts.includes(scriptName)) {
        currentSettings.allowedScripts.push(scriptName);
      }
    } else {
      currentSettings.allowedScripts = currentSettings.allowedScripts.filter(s => s !== scriptName);
    }
    queueSaveSettings();
  }

  if (cyrillicToggle) cyrillicToggle.addEventListener('change', (e) => toggleScript('Cyrillic', e.target.checked));
  if (greekToggle) greekToggle.addEventListener('change', (e) => toggleScript('Greek', e.target.checked));
  if (experimentalToggle) experimentalToggle.addEventListener('change', (e) => toggleScript('Experimental (All other scripts)', e.target.checked));

  // Primary Mode Radio Buttons (mutually exclusive)
  const primaryModes = document.querySelectorAll('input[name="primary-mode"]');
  if (primaryModes) {
    primaryModes.forEach(radio => {
      radio.addEventListener('change', (e) => {
        currentSettings.primaryMode = e.target.value;
        queueSaveSettings();
      });
    });
  }

  // Additive Feature Checkboxes (combinable)
  if (focusToggle) focusToggle.addEventListener('change', (e) => {
    currentSettings.focusEnabled = e.target.checked;
    queueSaveSettings();
  });

  if (bwToggle) bwToggle.addEventListener('change', (e) => {
    currentSettings.bwEnabled = e.target.checked;
    queueSaveSettings();
  });

  if (hcToggle) hcToggle.addEventListener('change', (e) => {
    currentSettings.hcEnabled = e.target.checked;
    queueSaveSettings();
  });

  if (nightLightToggle) nightLightToggle.addEventListener('change', (e) => {
    currentSettings.nightLightEnabled = e.target.checked;
    queueSaveSettings();
  });

  if (adhdToggle) adhdToggle.addEventListener('change', (e) => {
    currentSettings.adhdEnabled = e.target.checked;
    queueSaveSettings();
  });

  if (readerToggle) readerToggle.addEventListener('change', (e) => {
    currentSettings.readerModeEnabled = e.target.checked;
    queueSaveSettings();
  });

  // Tab Switching Logic
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  if (tabBtns) {
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        if (tabContents) tabContents.forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        const targetId = btn.getAttribute('data-target');
        const targetEl = document.getElementById(targetId);
        if (targetEl) targetEl.classList.add('active');
      });
    });
  }

  if (blacklistBtn) {
    blacklistBtn.addEventListener('click', () => {
      const isBlacklisted = currentSettings.blacklist.includes(currentHostname);
      if (isBlacklisted) {
        currentSettings.blacklist = currentSettings.blacklist.filter(h => h !== currentHostname);
      } else {
        if (currentHostname) currentSettings.blacklist.push(currentHostname);
      }
      updateBlacklistBtnUI(!isBlacklisted);
      queueSaveSettings();
    });
  }
}

function updateBlacklistBtnUI(isBlacklisted) {
  if (blacklistBtn) {
    if (isBlacklisted) {
      blacklistBtn.textContent = "Enable on this site";
      blacklistBtn.classList.add('blacklisted');
    } else {
      blacklistBtn.textContent = "Disable on this site";
      blacklistBtn.classList.remove('blacklisted');
    }
  }
}

function queueSaveSettings() {
  notifyActiveTab(currentSettings);
  if (saveTimeout) clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    chrome.storage.sync.set(currentSettings);
  }, 250);
}

function notifyActiveTab(settingsPayload) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { 
        action: "settings_updated",
        settings: settingsPayload 
      }).catch(() => {
        if (currentDomainEl) {
          currentDomainEl.textContent = "⚠️ Cannot modify this page";
          currentDomainEl.style.color = "#d32f2f";
        }
        disableAllInputs();
      });
    }
  });
}

function disableAllInputs() {
  document.querySelectorAll('input, button, select').forEach(el => el.disabled = true);
  document.querySelectorAll('.slider').forEach(el => {
    el.style.backgroundColor = '#eaeaea';
    el.style.cursor = 'not-allowed';
  });
}

document.addEventListener('DOMContentLoaded', init);
