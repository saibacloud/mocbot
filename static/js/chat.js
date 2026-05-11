const CAT_ASCII = ` ／l、\n（ﾟ､ ｡７\n |、ﾞ~ヽ\n  じしf_,)`;
const SVG_NS = 'http://www.w3.org/2000/svg';

export function buildMochaCat() {
  const container = document.createElement('div');
  container.className = 'cat-container';

  const pre = document.createElement('pre');
  pre.className = 'cat-watermark';
  pre.textContent = CAT_ASCII;
  container.appendChild(pre);

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'cat-tail');
  svg.setAttribute('viewBox', '-30 0 80 80');
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('d', 'M 0 64 Q 10 32 5 0');
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke', 'currentColor');
  path.setAttribute('stroke-width', '2.2');
  path.setAttribute('stroke-linecap', 'round');
  svg.appendChild(path);
  container.appendChild(svg);

  _animateTail(path);
  return container;
}

export function showEmpty() {
  const main = document.getElementById('chat-main');
  main.innerHTML = '';

  const wrap = document.createElement('div');
  wrap.className = 'chat-empty';
  wrap.appendChild(buildMochaCat());
  main.appendChild(wrap);
}

function _animateTail(path) {
  let start = null;
  function step(ts) {
    if (!path.isConnected) return;
    if (start === null) start = ts;
    const t = (ts - start) / 1000;
    const swing = Math.sin(t * 1.1) * 11 + Math.sin(t * 2.3) * 4;
    const cp1x = 0 + swing * 1.2;
    const cp2x = 18 - swing * 1.4;
    const ex = 8 + swing * 0.2;
    path.setAttribute('d', `M 0 64 C ${cp1x} 52 ${cp2x} 16 ${ex} 0`);
    requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

export function renderMessages(messages) {
  const main = document.getElementById('chat-main');
  main.innerHTML = '';
  if (messages.length === 0) {
    showEmpty();
    return;
  }
  for (const msg of messages) {
    _appendEl(msg.role, msg.content);
  }
  _scrollBottom();
}

export function appendUserMessage(text) {
  _clearEmpty();
  _appendEl('user', text);
  _scrollBottom();
}

export function appendStreamingPlaceholder() {
  _clearEmpty();
  const main = document.getElementById('chat-main');

  const dotsRow = _makeRow('assistant');
  const dotsBubble = document.createElement('div');
  dotsBubble.className = 'msg-bubble assistant';
  dotsBubble.innerHTML = '<span class="thinking-dots"><span></span><span></span><span></span></span>';
  dotsRow.appendChild(dotsBubble);
  main.appendChild(dotsRow);
  _scrollBottom();

  let thinkingDetails = null;
  let thinkingTextEl = null;
  let thinkingAccum = '';
  let contentBubble = null;
  let contentTextEl = null;
  let contentCursorEl = null;
  let contentAccum = '';

  function _showThinking() {
    if (thinkingDetails) return;
    if (dotsRow.parentElement) dotsRow.remove();
    const row = _makeRow('assistant');
    thinkingDetails = document.createElement('details');
    thinkingDetails.className = 'msg-thinking';
    thinkingDetails.open = true;
    const summary = document.createElement('summary');
    summary.innerHTML = '<span class="thinking-label">thinking</span><span class="thinking-dots inline"><span></span><span></span><span></span></span>';
    thinkingTextEl = document.createElement('div');
    thinkingTextEl.className = 'thinking-text';
    thinkingDetails.appendChild(summary);
    thinkingDetails.appendChild(thinkingTextEl);
    row.appendChild(thinkingDetails);
    main.appendChild(row);
  }

  function _showContent() {
    if (contentBubble) return;
    if (thinkingDetails) {
      thinkingDetails.open = false;
      thinkingDetails.classList.add('done');
      const inlineDots = thinkingDetails.querySelector('.thinking-dots.inline');
      if (inlineDots) inlineDots.remove();
    }
    if (dotsRow.parentElement) dotsRow.remove();
    const row = _makeRow('assistant');
    contentBubble = document.createElement('div');
    contentBubble.className = 'msg-bubble assistant';
    contentTextEl = document.createElement('span');
    contentCursorEl = document.createElement('span');
    contentCursorEl.className = 'streaming-cursor';
    contentBubble.appendChild(contentTextEl);
    contentBubble.appendChild(contentCursorEl);
    row.appendChild(contentBubble);
    main.appendChild(row);
  }

  return {
    updateThinking(chunk) {
      _showThinking();
      thinkingAccum += chunk;
      thinkingTextEl.textContent = thinkingAccum;
      _scrollBottom();
    },
    update(chunk) {
      _showContent();
      contentAccum += chunk;
      contentTextEl.textContent = contentAccum;
      _scrollBottom();
    },
    finalize() {
      if (contentCursorEl) contentCursorEl.remove();
      if (!contentBubble) {
        _showContent();
        contentTextEl.textContent = '(no response)';
        if (contentCursorEl) contentCursorEl.remove();
      }
      _scrollBottom();
    },
  };
}

function _makeRow(role) {
  const row = document.createElement('div');
  row.className = `msg-row ${role}`;
  return row;
}

function _clearEmpty() {
  const empty = document.querySelector('.chat-empty');
  if (empty) empty.remove();
}

function _appendEl(role, content) {
  const main = document.getElementById('chat-main');
  const row = document.createElement('div');
  row.className = `msg-row ${role}`;
  const bubble = document.createElement('div');
  bubble.className = `msg-bubble ${role}`;
  bubble.textContent = content;
  row.appendChild(bubble);
  main.appendChild(row);
  return bubble;
}

function _scrollBottom() {
  const main = document.getElementById('chat-main');
  main.scrollTop = main.scrollHeight;
}
