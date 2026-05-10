const CAT_ASCII = `   ／l、\n （ﾟ､ ｡７\n  |、ﾞ~ヽ\n  じしf_,)ノ `;

export function showEmpty() {
  const main = document.getElementById('chat-main');
  main.innerHTML = '';
  const pre = document.createElement('pre');
  pre.className = 'chat-empty cat-watermark';
  pre.textContent = CAT_ASCII;
  main.appendChild(pre);
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
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble assistant';

  const dots = document.createElement('span');
  dots.className = 'thinking-dots';
  dots.innerHTML = '<span></span><span></span><span></span>';
  bubble.appendChild(dots);

  row.appendChild(bubble);
  main.appendChild(row);
  _scrollBottom();

  let accumulated = '';
  let textEl = null;
  let cursorEl = null;

  return {
    update(chunk) {
      if (!textEl) {
        bubble.innerHTML = '';
        textEl = document.createElement('span');
        cursorEl = document.createElement('span');
        cursorEl.className = 'streaming-cursor';
        bubble.appendChild(textEl);
        bubble.appendChild(cursorEl);
      }
      accumulated += chunk;
      textEl.textContent = accumulated;
      _scrollBottom();
    },
    finalize() {
      if (cursorEl) cursorEl.remove();
      if (!textEl) {
        bubble.innerHTML = '';
        bubble.textContent = '(no response)';
      }
      _scrollBottom();
    },
  };
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
