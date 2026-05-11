import * as api from './api.js';

let _sessions = [];
let _activeId = null;
let _onSelect = null;
let _onDelete = null;
let _modelLabels = {};

export function init({ onSelect, onDelete }) {
  _onSelect = onSelect;
  _onDelete = onDelete;
}

export function setModels(models) {
  _modelLabels = Object.fromEntries(models.map(m => [m.id, m.label]));
  _render();
}

export async function load() {
  _sessions = await api.getSessions();
  _render();
}

export function setActive(id) {
  _activeId = id;
  _render();
}

export function get(id) {
  return _sessions.find(s => s.id === id);
}

export function updateTitle(sessionId, title) {
  const s = _sessions.find(s => s.id === sessionId);
  if (s) { s.title = title; _render(); }
}

export function prepend(session) {
  _sessions.unshift(session);
  _render();
}

export function remove(id) {
  _sessions = _sessions.filter(s => s.id !== id);
  _render();
}

function _relativeTime(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const h = diffMs / 3_600_000;
  if (h < 1) return 'just now';
  if (h < 24) return `${Math.floor(h)}h ago`;
  return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' });
}

function _modelLabel(model) {
  if (!model) return '';
  return _modelLabels[model] || model;
}

function _render() {
  const list = document.getElementById('session-list');
  list.innerHTML = '';

  for (const s of _sessions) {
    const el = document.createElement('div');
    el.className = 'session-item' + (s.id === _activeId ? ' active' : '');

    const title = s.title || 'new chat';

    el.innerHTML = `
      <div class="session-title">${_esc(title)}</div>
      <div class="session-meta">
        <span class="session-date">${_relativeTime(s.updated_at)}</span>
        <span class="session-model">${_esc(_modelLabel(s.model))}</span>
      </div>
      <button class="session-delete" data-id="${s.id}" title="Delete">×</button>
    `;

    el.addEventListener('click', e => {
      if (e.target.classList.contains('session-delete')) return;
      _onSelect?.(s.id);
    });

    el.querySelector('.session-delete').addEventListener('click', e => {
      e.stopPropagation();
      _onDelete?.(s.id);
    });

    list.appendChild(el);
  }
}

function _esc(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
