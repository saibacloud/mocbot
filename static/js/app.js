import * as api from './api.js';
import * as sessions from './sessions.js';
import * as chat from './chat.js';

let _username = null;
let _activeSessionId = null;
let _models = [];
let _sending = false;

async function _boot() {
  const token = api.getToken();
  if (token) {
    const user = await api.verifyToken(token).catch(() => null);
    if (user) {
      _username = user;
      await _showApp();
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

  _models = await api.getModels();
  _populateModelSelect();

  sessions.init({ onSelect: _loadSession, onDelete: _deleteSession });
  sessions.setModels(_models);
  await sessions.load();
  chat.showEmpty();
}

function _populateModelSelect() {
  const sel = document.getElementById('model-select');
  sel.innerHTML = '';
  for (const m of _models) {
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = m.label;
    sel.appendChild(opt);
  }
}

function _setSelectedModel(model) {
  if (!model) return;
  const sel = document.getElementById('model-select');
  if ([...sel.options].some(o => o.value === model)) sel.value = model;
}

async function _loadSession(id) {
  _activeSessionId = id;
  sessions.setActive(id);
  const session = sessions.get(id);
  if (session) _setSelectedModel(session.model);
  document.getElementById('model-select').disabled = true;
  const messages = await api.getMessages(id);
  chat.renderMessages(messages);
}

async function _deleteSession(id) {
  await api.deleteSession(id);
  sessions.remove(id);
  if (_activeSessionId === id) _resetToNew();
}

function _resetToNew() {
  _activeSessionId = null;
  sessions.setActive(null);
  document.getElementById('model-select').disabled = false;
  chat.showEmpty();
}

async function _newChat(model) {
  const session = await api.createSession(model);
  const full = { ...session, title: null, updated_at: session.created_at, model };
  sessions.prepend(full);
  await _loadSession(session.id);
}

async function _send(text) {
  if (_sending || !text.trim()) return;
  if (!_activeSessionId) {
    const model = document.getElementById('model-select').value;
    await _newChat(model);
  }

  _sending = true;
  const input = document.getElementById('chat-input');
  input.disabled = true;

  chat.appendUserMessage(text);
  const stream = chat.appendStreamingPlaceholder();

  try {
    await api.streamChat(_activeSessionId, text, {
      onThinking(chunk) { stream.updateThinking(chunk); },
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
    await _showApp();
  } else {
    document.getElementById('login-error').textContent = 'invalid token.';
  }
});

document.getElementById('new-chat-btn').addEventListener('click', _resetToNew);

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
