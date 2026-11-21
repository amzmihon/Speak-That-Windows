// ============================================================
// ADHD Bionic Reader - High Performance Content Script
// Built following The Modern Web Guidance:
// - Non-blocking task chunking via scheduler.yield()
// - Direct DOM text-node transformation (guaranteed visible bolding)
// - Clean reversibility (undoBionic restores pure DOM text)
// - Native C++ TreeWalker DOM traversal (O(N) single-pass)
// - Zero layout-thrashing: position:fixed floating TTS (no scroll queries)
// - Smart debounced MutationObserver with recursion guards
// ============================================================

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
let isBionicActive = false;
let isTransforming = false;
let currentJobId = 0;
let observer = null;
let lastUrl = location.href;

// Tags and selectors to skip during text walk
const EXCLUDED_TAGS = new Set([
  'SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'SELECT', 'OPTION',
  'NOSCRIPT', 'CODE', 'PRE', 'SVG', 'CANVAS', 'VIDEO', 'AUDIO',
  'IFRAME', 'OBJECT', 'EMBED', 'MATH', 'ADHD-BORDER-HOST'
]);

// Non-blocking cooperative yield to browser main thread
async function yieldToMain() {
  if (typeof scheduler !== 'undefined' && typeof scheduler.yield === 'function') {
    return scheduler.yield();
  }
  return new Promise(resolve => setTimeout(resolve, 0));
}

// Word Fixation Length Calculation
function getBoldLength(word, ratio) {
  const len = word.length;
  if (len <= 1) return 1;
  if (len <= 3) return Math.min(len, Math.max(1, Math.ceil(len * ratio)));
  if (len === 4) return Math.min(3, Math.max(1, Math.ceil(len * ratio)));
  return Math.min(len - 1, Math.max(1, Math.ceil(len * ratio)));
}

// Compile word regex based on script settings
function getWordRegex() {
  const scripts = currentSettings.allowedScripts || ['Latin'];
  if (scripts.includes('Experimental (All other scripts)')) {
    return /([\p{L}\p{N}]+)|([^\p{L}\p{N}]+)/gu;
  }
  const scriptPattern = scripts.map(s => `\\p{Script=${s}}`).join('');
  return new RegExp(`([${scriptPattern}\\p{N}]+)|([^${scriptPattern}\\p{N}]+)`, 'gu');
}

// Transform a single text node into Bionic Reading elements
function bionicTransformTextNode(textNode, regex, ratio) {
  if (!textNode || !textNode.parentNode) return;
  const parent = textNode.parentNode;
  if (parent.closest && parent.closest('[data-bionic="1"], [data-bionic-bold="1"], b[data-bionic="1"], adhd-border-host, #bionic-reader-overlay')) {
    return;
  }
  const text = textNode.nodeValue;
  if (!text || text.trim().length === 0) return;

  regex.lastIndex = 0;
  let hasMatch = false;
  let match;

  const wrapper = document.createElement('span');
  wrapper.setAttribute('data-bionic', '1');

  while ((match = regex.exec(text)) !== null) {
    if (match[1]) {
      hasMatch = true;
      const word = match[1];
      const boldLen = getBoldLength(word, ratio);
      const boldPart = word.slice(0, boldLen);
      const restPart = word.slice(boldLen);

      const b = document.createElement('b');
      b.setAttribute('data-bionic-bold', '1');
      b.textContent = boldPart;
      wrapper.appendChild(b);

      if (restPart) {
        wrapper.appendChild(document.createTextNode(restPart));
      }
    } else if (match[2]) {
      wrapper.appendChild(document.createTextNode(match[2]));
    }
  }

  if (hasMatch) {
    if (parent && textNode.parentNode === parent) {
      parent.replaceChild(wrapper, textNode);
    }
  }
}

// Revert all bionic bolding across a container
function undoBionic(container) {
  const root = container || document.body;
  if (!root) return;

  const bionicSpans = root.querySelectorAll('span[data-bionic="1"]');
  const parentsToNormalize = new Set();

  bionicSpans.forEach(span => {
    const parent = span.parentNode;
    if (parent) {
      parentsToNormalize.add(parent);
      span.replaceWith(document.createTextNode(span.textContent));
    }
  });

  const bElements = root.querySelectorAll('b[data-bionic="1"], b[data-bionic-bold="1"]');
  bElements.forEach(b => {
    const parent = b.parentNode;
    if (parent) {
      parentsToNormalize.add(parent);
      b.replaceWith(document.createTextNode(b.textContent));
    }
  });

  parentsToNormalize.forEach(p => {
    try {
      p.normalize();
    } catch (e) {}
  });
}

let fullPageJobId = 0;

// Non-blocking Tree Walker with scheduler.yield()
async function processSubtree(rootNode, isFullPage = false) {
  if (!currentSettings.enabled || isBlacklistedDomain()) return;
  if (!rootNode || !rootNode.isConnected) return;

  const jobId = isFullPage ? ++fullPageJobId : 0;
  const regex = getWordRegex();
  const ratio = currentSettings.fixationRatio || 0.4;

  const walker = document.createTreeWalker(
    rootNode,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const val = node.nodeValue;
        if (!val || val.trim().length === 0) return NodeFilter.FILTER_REJECT;
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        const tag = parent.tagName;
        if (EXCLUDED_TAGS.has(tag)) return NodeFilter.FILTER_REJECT;
        if (parent.closest && parent.closest('[data-bionic="1"], [data-bionic-bold="1"], b[data-bionic], adhd-border-host, #bionic-reader-overlay, [contenteditable="true"]')) {
          return NodeFilter.FILTER_REJECT;
        }
        if (parent.isContentEditable) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );

  const textNodes = [];
  while (walker.nextNode()) {
    textNodes.push(walker.currentNode);
  }

  // Chunk processing: 6ms budget per frame to preserve 60fps (INP < 16ms)
  let i = 0;
  const total = textNodes.length;
  isTransforming = true;

  try {
    while (i < total) {
      if (isFullPage && jobId !== fullPageJobId) return; // Stale full-page job cancelled

      const startPerf = performance.now();
      while (i < total && (performance.now() - startPerf) < 6) {
        const textNode = textNodes[i++];
        if (textNode && textNode.isConnected && textNode.parentNode) {
          bionicTransformTextNode(textNode, regex, ratio);
        }
      }

      if (i < total) {
        await yieldToMain();
      }
    }
  } finally {
    isTransforming = false;
  }
}

// ============================================================
// MUTATION OBSERVER (Batched, Debounced, No Layout Thrashing)
// ============================================================

let mutationQueue = new Set();
let mutationTimeout = null;

function handleMutations(mutations) {
  checkUrlChange();
  if (!currentSettings.enabled || isBlacklistedDomain()) return;

  let hasAdded = false;

  for (let i = 0; i < mutations.length; i++) {
    const mutation = mutations[i];

    for (let k = 0; k < mutation.addedNodes.length; k++) {
      const added = mutation.addedNodes[k];
      if (added.nodeType === Node.ELEMENT_NODE) {
        const tag = added.tagName;
        if (tag === 'HEAD' || EXCLUDED_TAGS.has(tag)) continue;
        if (added.hasAttribute && (added.hasAttribute('data-bionic') || added.hasAttribute('data-bionic-bold'))) continue;
        if (added.closest && added.closest('[data-bionic="1"], [data-bionic-bold="1"], adhd-border-host, #bionic-reader-overlay')) continue;
        mutationQueue.add(added);
        hasAdded = true;
      } else if (added.nodeType === Node.TEXT_NODE) {
        const parent = added.parentElement;
        if (parent && !EXCLUDED_TAGS.has(parent.tagName)) {
          if (!parent.closest || !parent.closest('[data-bionic="1"], [data-bionic-bold="1"], adhd-border-host, #bionic-reader-overlay')) {
            mutationQueue.add(added);
            hasAdded = true;
          }
        }
      }
    }
  }

  if (hasAdded) {
    if (mutationTimeout) clearTimeout(mutationTimeout);
    mutationTimeout = setTimeout(flushMutationQueue, 150);
  }
}

async function flushMutationQueue() {
  if (mutationQueue.size === 0) return;
  const nodes = Array.from(mutationQueue);
  mutationQueue.clear();

  const regex = getWordRegex();
  const ratio = currentSettings.fixationRatio || 0.4;

  // Deduplicate nested elements
  const topNodes = nodes.filter(node => {
    let parent = node.parentNode;
    while (parent && parent !== document.body && parent !== document.documentElement) {
      if (nodes.includes(parent)) return false;
      parent = parent.parentNode;
    }
    return true;
  });

  for (const node of topNodes) {
    if (node.isConnected) {
      if (node.nodeType === Node.TEXT_NODE) {
        bionicTransformTextNode(node, regex, ratio);
      } else {
        await processSubtree(node, false);
      }
    }
  }
}

function startObserver() {
  if (observer) return;
  observer = new MutationObserver(handleMutations);
  observer.observe(document.documentElement || document.body, {
    childList: true,
    subtree: true
  });
}

function stopObserver() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  if (mutationTimeout) clearTimeout(mutationTimeout);
  mutationQueue.clear();
}

function isBlacklistedDomain() {
  return currentSettings.blacklist && currentSettings.blacklist.includes(window.location.hostname);
}

function checkUrlChange() {
  if (lastUrl !== location.href) {
    lastUrl = location.href;
    if (isBlacklistedDomain() || !currentSettings.enabled) {
      undoBionic(document.body);
    } else {
      setTimeout(() => {
        if (document.body) processSubtree(document.body);
      }, 300);
    }
  }
}

// ============================================================
// DYNAMIC BIONIC CSS STYLES
// ============================================================

function injectStyles(settings) {
  let style = document.getElementById('bionic-styles');
  if (!style) {
    style = document.createElement('style');
    style.id = 'bionic-styles';
    style.setAttribute('data-darkreader-ignore', 'true');
    const target = document.head || document.documentElement;
    if (target) target.appendChild(style);
  }

  const boldness = settings ? (settings.bionicBoldness || 1.0) : 1.0;
  let fontWeight = 800;
  let strokeCSS = '';

  if (boldness >= 2.0) {
    fontWeight = 900;
    const strokeWidth = ((boldness - 1.5) * 0.35).toFixed(2);
    strokeCSS = `-webkit-text-stroke: ${strokeWidth}px currentColor;`;
  } else if (boldness > 1.0) {
    fontWeight = 850;
    const strokeWidth = ((boldness - 1.0) * 0.25).toFixed(2);
    strokeCSS = `-webkit-text-stroke: ${strokeWidth}px currentColor;`;
  } else if (boldness < 0.8) {
    fontWeight = 700;
  }

  style.textContent = `
    span[data-bionic="1"] {
      display: inline !important;
      font-weight: inherit !important;
      color: inherit !important;
    }
    b[data-bionic-bold="1"], b[data-bionic="1"] {
      font-weight: ${fontWeight} !important;
      display: inline !important;
      color: inherit !important;
      ${strokeCSS}
    }
  `;
}

// ============================================================
// VISUAL ENVIRONMENT ENGINE (Isolated & Efficient)
// ============================================================

let adhdBorderHost = null;

function applyVisualSettings(settings) {
  removeADHDOverlays();

  const mode = settings.primaryMode || 'light';

  if (typeof DarkReader !== 'undefined') {
    const isDarkReaderNeeded = (mode === 'gray' || mode === 'black' || settings.bwEnabled || settings.nightLightEnabled || settings.hcEnabled);

    if (isDarkReaderNeeded) {
      const theme = {
        brightness: 100,
        contrast: settings.hcEnabled ? 140 : 100,
        sepia: settings.nightLightEnabled ? 35 : 0,
        grayscale: settings.bwEnabled ? 100 : 0,
        mode: (mode === 'gray' || mode === 'black') ? 1 : 0
      };

      if (mode === 'gray') {
        theme.darkSchemeBackgroundColor = '#2e2e2e';
        theme.darkSchemeTextColor = '#e0e0e0';
      } else if (mode === 'black') {
        theme.darkSchemeBackgroundColor = '#000000';
        theme.darkSchemeTextColor = '#e0e0e0';
      }

      try {
        DarkReader.setFetchMethod(window.fetch);
        DarkReader.enable(theme);
      } catch (e) {
        console.warn('[ADHD Bionic Reader] DarkReader enable:', e);
      }
    } else {
      try {
        DarkReader.disable();
      } catch (e) {}
    }
  }

  // Focus Engine
  let focusStyleEl = document.getElementById('adhd-focus-engine');
  if (settings.focusEnabled) {
    if (!focusStyleEl) {
      focusStyleEl = document.createElement('style');
      focusStyleEl.id = 'adhd-focus-engine';
      const target = document.head || document.documentElement;
      if (target) target.appendChild(focusStyleEl);
    }
    focusStyleEl.textContent = `
      img:not([alt*="logo" i]), video, iframe, [class*="ad-" i], [id*="ad-" i] {
        opacity: 0.1 !important;
        filter: grayscale(100%) !important;
        transition: opacity 0.25s ease !important;
      }
      img:hover, video:hover, iframe:hover {
        opacity: 1 !important;
        filter: none !important;
      }
    `;
  } else if (focusStyleEl) {
    focusStyleEl.remove();
  }

  // ADHD Peripheral Breathing Border
  if (settings.adhdEnabled) {
    setupADHDOverlays();
  }
}

function setupADHDOverlays() {
  if (adhdBorderHost) return;
  adhdBorderHost = document.createElement('adhd-border-host');
  adhdBorderHost.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 2147483646; pointer-events: none;';

  const shadow = adhdBorderHost.attachShadow({ mode: 'closed' });
  const wrapper = document.createElement('div');

  const style = document.createElement('style');
  style.textContent = `
    .border-bar {
      position: fixed;
      pointer-events: none;
      background: linear-gradient(90deg, #2196F3, #9C27B0, #2196F3);
      background-size: 200% 100%;
      animation: breathe 5s ease-in-out infinite;
      opacity: 0.35;
      will-change: opacity, background-position;
    }
    @keyframes breathe {
      0%, 100% { background-position: 0% 50%; opacity: 0.45; }
      50% { background-position: 100% 50%; opacity: 0.15; }
    }
    .top { top: 0; left: 0; right: 0; height: 5px; }
    .bottom { bottom: 0; left: 0; right: 0; height: 5px; }
    .left { top: 0; bottom: 0; left: 0; width: 5px; background: linear-gradient(180deg, #2196F3, #9C27B0, #2196F3); background-size: 100% 200%; }
    .right { top: 0; bottom: 0; right: 0; width: 5px; background: linear-gradient(180deg, #2196F3, #9C27B0, #2196F3); background-size: 100% 200%; }
  `;

  const t = document.createElement('div'); t.className = 'border-bar top';
  const b = document.createElement('div'); b.className = 'border-bar bottom';
  const l = document.createElement('div'); l.className = 'border-bar left';
  const r = document.createElement('div'); r.className = 'border-bar right';

  wrapper.appendChild(style);
  wrapper.appendChild(t);
  wrapper.appendChild(b);
  wrapper.appendChild(l);
  wrapper.appendChild(r);
  shadow.appendChild(wrapper);

  (document.body || document.documentElement).appendChild(adhdBorderHost);
}

function removeADHDOverlays() {
  if (adhdBorderHost) {
    adhdBorderHost.remove();
    adhdBorderHost = null;
  }
}

// ============================================================
// READER MODE (Distraction-Free Clean Article View)
// ============================================================

let readerModeOverlay = null;

function enableReaderMode() {
  if (readerModeOverlay || typeof Readability === 'undefined') return;

  let article = null;
  try {
    const documentClone = document.cloneNode(true);
    article = new Readability(documentClone).parse();
  } catch (e) {
    console.warn('[ADHD Bionic Reader] Readability error:', e);
    return;
  }

  if (!article || !article.content) return;

  Array.from(document.body.children).forEach(child => {
    if (child.id !== 'bionic-reader-overlay' && !child.tagName.includes('HOST')) {
      child.dataset.bionicPrevDisplay = child.style.display || '';
      child.style.display = 'none';
    }
  });

  readerModeOverlay = document.createElement('div');
  readerModeOverlay.id = 'bionic-reader-overlay';
  const shadow = readerModeOverlay.attachShadow({ mode: 'closed' });

  const parser = new DOMParser();
  const parsedDoc = parser.parseFromString(article.content, 'text/html');
  parsedDoc.querySelectorAll('script, noscript, object, embed, iframe, link').forEach(el => el.remove());
  parsedDoc.querySelectorAll('*').forEach(el => {
    Array.from(el.attributes).forEach(attr => {
      if (attr.name.toLowerCase().startsWith('on')) {
        el.removeAttribute(attr.name);
      }
    });
  });

  const isDark = currentSettings && (currentSettings.primaryMode === 'gray' || currentSettings.primaryMode === 'black');
  const bg = isDark ? '#1a1a1a' : '#fbfbfb';
  const textCol = isDark ? '#f0f0f0' : '#222222';

  const style = document.createElement('style');
  style.textContent = `
    :host {
      display: block;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: ${bg};
      color: ${textCol};
      z-index: 2147483645;
      overflow-y: auto;
      padding: 40px 24px 80px;
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, serif;
    }
    .reader-article {
      max-width: 740px;
      margin: 0 auto;
      font-size: 19px;
      line-height: 1.75;
      letter-spacing: 0.2px;
    }
    h1 {
      font-size: 2.2em;
      line-height: 1.25;
      margin-bottom: 24px;
      font-weight: 800;
    }
    img {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      margin: 20px 0;
    }
    p { margin-bottom: 20px; }
    b[data-bionic="1"] { font-weight: 700 !important; color: inherit !important; }
    .close-btn {
      position: fixed;
      top: 20px;
      right: 24px;
      background: rgba(0,0,0,0.1);
      color: inherit;
      border: none;
      padding: 8px 16px;
      border-radius: 20px;
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
      backdrop-filter: blur(8px);
    }
    .close-btn:hover {
      background: rgba(0,0,0,0.2);
    }
  `;

  const articleWrapper = document.createElement('div');
  articleWrapper.className = 'reader-article';

  const titleEl = document.createElement('h1');
  titleEl.textContent = article.title;
  articleWrapper.appendChild(titleEl);

  while (parsedDoc.body.firstChild) {
    articleWrapper.appendChild(parsedDoc.body.firstChild);
  }

  const closeBtn = document.createElement('button');
  closeBtn.className = 'close-btn';
  closeBtn.textContent = '✕ Exit Reader';
  closeBtn.addEventListener('click', () => {
    chrome.storage.sync.set({ readerModeEnabled: false });
    disableReaderMode();
  });

  shadow.appendChild(style);
  shadow.appendChild(closeBtn);
  shadow.appendChild(articleWrapper);

  document.body.appendChild(readerModeOverlay);

  processSubtree(articleWrapper);
}

function disableReaderMode() {
  if (!readerModeOverlay) return;

  Array.from(document.body.children).forEach(child => {
    if (child.dataset.bionicPrevDisplay !== undefined) {
      child.style.display = child.dataset.bionicPrevDisplay;
      delete child.dataset.bionicPrevDisplay;
    }
  });

  readerModeOverlay.remove();
  readerModeOverlay = null;
}

// ============================================================
// SETTINGS APPLICATION LIFECYCLE
// ============================================================

async function applySettingsAndRender(settings, isInitial = false) {
  const prevSettings = { ...currentSettings };
  currentSettings = settings;

  injectStyles(currentSettings);
  applyVisualSettings(currentSettings);

  const isBlacklisted = isBlacklistedDomain();
  const shouldBeActive = currentSettings.enabled && !isBlacklisted;

  if (shouldBeActive) {
    if (currentSettings.readerModeEnabled) {
      enableReaderMode();
    } else {
      disableReaderMode();
    }

    const needsRehighlight = isInitial || (
      !isBionicActive ||
      prevSettings.fixationRatio !== currentSettings.fixationRatio ||
      JSON.stringify(prevSettings.allowedScripts) !== JSON.stringify(currentSettings.allowedScripts)
    );

    if (needsRehighlight) {
      if (!isInitial) {
        undoBionic(document.body);
      }
      isBionicActive = true;
      if (document.body) {
        await processSubtree(document.body, true);
      }
    }

    startObserver();
  } else {
    disableReaderMode();
    stopObserver();
    undoBionic(document.body);
    isBionicActive = false;
  }
}

// Runtime messaging listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "ping") {
    sendResponse({ status: "ok" });
  } else if (request.action === "settings_updated" && request.settings) {
    applySettingsAndRender(request.settings);
  }
});

// SPA URL change detection via History API
const nativePushState = history.pushState;
history.pushState = function() {
  nativePushState.apply(this, arguments);
  checkUrlChange();
};

const nativeReplaceState = history.replaceState;
history.replaceState = function() {
  nativeReplaceState.apply(this, arguments);
  checkUrlChange();
};

window.addEventListener('popstate', checkUrlChange);

// Initialize on page load (Robust dual-stage with zero cold-start delay)
let hasInitialized = false;

function initPage(settings) {
  if (hasInitialized) return;
  hasInitialized = true;
  applySettingsAndRender(settings || currentSettings, true);
}

if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
  try {
    chrome.storage.sync.get(DEFAULT_SETTINGS, (settings) => {
      const merged = { ...DEFAULT_SETTINGS, ...settings };
      if (!hasInitialized) {
        initPage(merged);
      } else {
        applySettingsAndRender(merged, false);
      }
    });
  } catch (e) {
    console.warn('[ADHD Bionic Reader] storage.sync error:', e);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initPage(), { once: true });
} else {
  // Run on next tick if DOM is already parsed/interactive
  setTimeout(() => initPage(), 0);
}
