const TOKEN_KEY = 'mocha_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
  };
}

export async function verifyToken(token) {
  const r = await fetch('/auth/verify', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!r.ok) return null;
  return (await r.json()).username;
}

export async function getModels() {
  const r = await fetch('/models', { headers: authHeaders() });
  if (!r.ok) throw new Error('Failed to load models');
  return r.json();
}

export async function getSessions() {
  const r = await fetch('/sessions', { headers: authHeaders() });
  if (!r.ok) throw new Error('Failed to load sessions');
  return r.json();
}

export async function createSession(model) {
  const r = await fetch('/sessions', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ model }),
  });
  if (!r.ok) throw new Error('Failed to create session');
  return r.json();
}

export async function deleteSession(id) {
  const r = await fetch(`/sessions/${id}`, { method: 'DELETE', headers: authHeaders() });
  if (!r.ok) throw new Error('Failed to delete session');
}

export async function getMessages(sessionId) {
  const r = await fetch(`/sessions/${sessionId}/messages`, { headers: authHeaders() });
  if (!r.ok) throw new Error('Failed to load messages');
  return r.json();
}

export async function getContext() {
  const r = await fetch('/context', { headers: authHeaders() });
  if (!r.ok) throw new Error('Failed to load context');
  return r.json();
}

export async function saveContext(context) {
  const r = await fetch('/context', {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ context }),
  });
  if (!r.ok) throw new Error('Failed to save context');
}

export async function streamChat(sessionId, message, { onChunk, onDone, onTitle }) {
  const response = await fetch(`/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ message }),
  });

  if (!response.ok) throw new Error('Chat request failed');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.chunk !== undefined) onChunk(data.chunk);
        if (data.done) onDone();
        if (data.title) onTitle(data.title);
      } catch {}
    }
  }
}
