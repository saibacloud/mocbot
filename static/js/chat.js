const CAT_ASCII = ` ／l、\n（ﾟ､ ｡７\n |、ﾞ~ヽ\n  じしf_,)ノ`;

export function showEmpty() {
  const main = document.getElementById('chat-main');
  main.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'chat-empty';
  const pre = document.createElement('pre');
  pre.className = 'cat-watermark';
  pre.textContent = CAT_ASCII;
  wrap.appendChild(pre);
  main.appendChild(wrap);
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
