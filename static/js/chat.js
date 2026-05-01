const CAT_ASCII = `   ／l、\n （ﾟ､ ｡７\n  |、ﾞ~ヽ\n  じしf_,)ノ `;

let _breatheInterval = null;

export function showEmpty() {
  _stopBreathe();
  const main = document.getElementById('chat-main');
  main.innerHTML = '';
  const pre = document.createElement('pre');
  pre.id = 'cat';
  pre.className = 'cat-empty';
  pre.textContent = CAT_ASCII;
  main.appendChild(pre);
  _startBreathe(pre);
}

export function renderMessages(messages) {
  _stopBreathe();
  const main = document.getElementById('chat-main');
  main.innerHTML = '';
  for (const msg of messages) {
    _appendEl(msg.role, msg.content);
  }
  _scrollBottom();
}

export function appendUserMessage(text) {
  _stopBreathe();
  _appendEl('user', text);
  _scrollBottom();
}

export function appendStreamingPlaceholder() {
  _stopBreathe();
  const el = _appendEl('assistant', '...');
  let accumulated = '';

  return {
    update(chunk) {
      accumulated += chunk;
      el.textContent = accumulated;
      _scrollBottom();
    },
    finalize() {
      _scrollBottom();
    },
  };
}

function _appendEl(role, content) {
  const main = document.getElementById('chat-main');
  const el = document.createElement('div');
  el.className = role === 'user' ? 'msg-you' : 'msg-mocha';
  el.textContent = content;
  main.appendChild(el);
  return el;
}

function _scrollBottom() {
  const main = document.getElementById('chat-main');
  main.scrollTop = main.scrollHeight;
}

function _startBreathe(el) {
  let up = false;
  _breatheInterval = setInterval(() => {
    up = !up;
    el.style.transform = up ? 'translateY(-5px)' : 'translateY(0)';
  }, 1500);
}

function _stopBreathe() {
  if (_breatheInterval) {
    clearInterval(_breatheInterval);
    _breatheInterval = null;
  }
}
