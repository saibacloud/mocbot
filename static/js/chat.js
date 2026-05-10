export function showEmpty() {
  const main = document.getElementById('chat-main');
  main.innerHTML = '';
  const div = document.createElement('div');
  div.className = 'chat-empty';
  div.textContent = 'start a new chat below';
  main.appendChild(div);
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
