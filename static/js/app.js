import * as api from './api.js';
import * as sessions from './sessions.js';
import * as chat from './chat.js';

let _username = null;
let _activeSessionId = null;
let _mocMode = true;
let _sending = false;

async function _boot() {
  const token = api.getToken();
  if (token) {
    const user = await api.verifyToken(token).catch(() => null);
    if (user) {
      _username = user;
      _showApp();
      return;
    }
  }
  _showLogin();
}

function _showLogin() {
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('app-screen').classList.remove('visible');
}

async function _showApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app-screen').classList.add('visible');
  document.getElementById('username-label').textContent = _username;

  sessions.init({ onSelect: _loadSession, onDelete: _deleteSession });
  await sessions.load();
  chat.showEmpty();
}

async function _loadSession(id) {
  _activeSessionId = id;
  sessions.setActive(id);
  const messages = await api.getMessages(id);
  chat.renderMessages(messages);
}

async function _deleteSession(id) {
  await api.deleteSession(id);
  sessions.remove(id);
  if (_activeSessionId === id) {
    _activeSessionId = null;
    chat.showEmpty();
  }
}

async function _newChat() {
  const mode = _mocMode ? 'moc' : 'serious';
  const session = await api.createSession(mode);
  const full = { ...session, title: null, updated_at: session.created_at, mode };
  sessions.prepend(full);
  await _loadSession(session.id);
}

async function _send(text) {
  if (_sending || !text.trim()) return;
  if (!_activeSessionId) await _newChat();

  _sending = true;
  const input = document.getElementById('chat-input');
  input.disabled = true;

  chat.appendUserMessage(text);
  const stream = chat.appendStreamingPlaceholder();

  try {
    await api.streamChat(_activeSessionId, text, {
      onChunk(chunk) { stream.update(chunk); },
      onDone() { stream.finalize(); },
      onTitle(title) { sessions.updateTitle(_activeSessionId, title); },
    });
  } finally {
    _sending = false;
    input.disabled = false;
    input.focus();
  }
}

document.getElementById('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const token = document.getElementById('token-input').value.trim();
  const user = await api.verifyToken(token).catch(() => null);
  if (user) {
    api.setToken(token);
    _username = user;
    _showApp();
  } else {
    document.getElementById('login-error').textContent = 'invalid token.';
  }
});

document.getElementById('mocmode-toggle').addEventListener('click', () => {
  _mocMode = !_mocMode;
  document.getElementById('mocmode-toggle').classList.toggle('active', _mocMode);
});

document.getElementById('new-chat-btn').addEventListener('click', _newChat);

document.getElementById('chat-form').addEventListener('submit', async e => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  await _send(text);
});

document.getElementById('context-btn').addEventListener('click', async () => {
  const { context } = await api.getContext();
  document.getElementById('context-textarea').value = context;
  document.getElementById('context-overlay').classList.add('visible');
});

document.getElementById('context-close').addEventListener('click', () => {
  document.getElementById('context-overlay').classList.remove('visible');
});

document.getElementById('context-save').addEventListener('click', async () => {
  const context = document.getElementById('context-textarea').value;
  await api.saveContext(context);
  document.getElementById('context-overlay').classList.remove('visible');
});

_boot();
