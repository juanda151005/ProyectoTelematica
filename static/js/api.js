/**
 * GroupsApp — API Client
 * Wraps all REST endpoints with JWT auth.
 */
class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.prefix = '/api/v1';
    this.token = localStorage.getItem('token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }

  get headers() {
    const h = { 'Content-Type': 'application/json' };
    if (this.token) h['Authorization'] = `Bearer ${this.token}`;
    return h;
  }

  async request(method, path, body = null, isForm = false) {
    const url = `${this.baseUrl}${this.prefix}${path}`;
    const opts = { method, headers: {} };

    if (this.token) opts.headers['Authorization'] = `Bearer ${this.token}`;

    if (body && isForm) {
      opts.body = body; // FormData, no Content-Type header
    } else if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }

    const res = await fetch(url, opts);
    const data = res.headers.get('content-type')?.includes('json')
      ? await res.json()
      : await res.text();

    if (!res.ok) {
      const msg = typeof data === 'object' ? data.detail || JSON.stringify(data) : data;
      throw new Error(msg);
    }
    return data;
  }

  // ===== Auth =====
  async register(username, password) {
    const data = await this.request('POST', '/auth/register', { username, password });
    this.setToken(data.access_token);
    return data;
  }

  async login(username, password) {
    const data = await this.request('POST', '/auth/login', { username, password });
    this.setToken(data.access_token);
    return data;
  }

  logout() {
    this.setToken(null);
  }

  // ===== Groups =====
  async getGroups() {
    return this.request('GET', '/groups');
  }

  async getMembers(groupId) {
    return this.request('GET', `/groups/${groupId}/members`);
  }

  async createGroup(name, settings = {}) {
    return this.request('POST', '/groups', { name, settings });
  }

  async addMember(groupId, username) {
    return this.request('POST', `/groups/${groupId}/members`, { username });
  }

  async startDM(userId) {
    return this.request('POST', `/groups/dm`, { user_id: userId });
  }

  async removeMember(groupId, userId) {
    return this.request('DELETE', `/groups/${groupId}/members/${userId}`);
  }

  async updateMemberRole(groupId, userId, role) {
    return this.request('PUT', `/groups/${groupId}/members/${userId}/role`, { role });
  }

  // ===== Messages =====
  async sendMessage(groupId, content, recipientId = null) {
    return this.request('POST', `/groups/${groupId}/messages`, {
      content,
      recipient_id: recipientId,
    });
  }

  async getMessages(groupId, limit = 50, offset = 0) {
    return this.request('GET', `/groups/${groupId}/messages?limit=${limit}&offset=${offset}`);
  }

  // ===== Files =====
  async uploadFile(groupId, file, content = null, recipientId = null) {
    const form = new FormData();
    form.append('group_id', groupId);
    form.append('file', file);
    if (content) form.append('content', content);
    if (recipientId) form.append('recipient_id', recipientId);
    return this.request('POST', '/messages/file', form, true);
  }

  // ===== Presence =====
  async getPresence(userId) {
    return this.request('GET', `/users/${userId}/presence`);
  }

  // ===== WebSocket =====
  connectWebSocket(groupId, onMessage, onClose) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/groups/${groupId}?token=${this.token}`;
    const ws = new WebSocket(url);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    ws.onclose = () => {
      if (onClose) onClose();
    };

    ws.onerror = (err) => {
      console.error('WS error:', err);
    };

    return ws;
  }

  // ===== Utility: parse JWT to extract user_id =====
  parseToken() {
    if (!this.token) return null;
    try {
      const payload = JSON.parse(atob(this.token.split('.')[1]));
      return payload;
    } catch {
      return null;
    }
  }

  getCurrentUserId() {
    const payload = this.parseToken();
    return payload ? payload.sub : null;
  }

  isAuthenticated() {
    if (!this.token) return false;
    const payload = this.parseToken();
    if (!payload || !payload.exp) return false;
    return payload.exp * 1000 > Date.now();
  }
}

// Export singleton
const api = new ApiClient();
