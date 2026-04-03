/**
 * GroupsApp — Main Application
 */
(function () {
  // ===== State =====
  const state = {
    currentUserId: null,
    currentUsername: null,
    groups: [],           // [{id, name, admin_id, settings}]
    activeGroupId: null,
    activeGroupData: null,
    messages: [],
    members: [],          // [{user_id, role, username}]
    ws: null,
    membersPanelOpen: false,
    usernameCache: {},    // userId -> username (populated from messages & members)
  };

  // ===== DOM refs =====
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // Views
  const authView = $('#auth-view');
  const chatView = $('#chat-view');

  // Auth
  const authTabs = $$('.auth-tab');
  const loginForm = $('#login-form');
  const registerForm = $('#register-form');
  const authError = $('#auth-error');

  // Sidebar
  const userAvatar = $('#user-avatar');
  const usernameDisplay = $('#username-display');
  const groupsList = $('#groups-list');

  // Chat
  const chatHeader = $('#chat-header');
  const chatGroupName = $('#chat-group-name');
  const chatMemberCount = $('#chat-member-count');
  const messagesContainer = $('#messages-container');
  const emptyChat = $('#empty-chat');
  const chatInputArea = $('#chat-input-area');
  const messageInput = $('#message-input');
  const btnSend = $('#btn-send');
  const btnAttach = $('#btn-attach');
  const fileInput = $('#file-input');
  const btnMembers = $('#btn-members');
  const btnLeave = $('#btn-leave');

  // Members panel
  const membersPanel = $('#members-panel');
  const membersList = $('#members-list');

  // Modals
  const modalOverlay = $('#modal-overlay');

  // Toast
  const toastContainer = $('#toast-container');

  // ===== Toast =====
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(30px)';
      toast.style.transition = '0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // ===== Modal =====
  function openModal(title, fields, onSubmit) {
    const modal = document.createElement('div');
    modal.className = 'modal';

    let fieldsHtml = fields.map(f => `
      <div class="form-group">
        <label>${f.label}</label>
        <input type="${f.type || 'text'}" id="modal-${f.id}" placeholder="${f.placeholder || ''}"
          ${f.minLength ? `minlength="${f.minLength}"` : ''} ${f.required ? 'required' : ''}>
      </div>
    `).join('');

    modal.innerHTML = `
      <h3>${title}</h3>
      ${fieldsHtml}
      <div class="modal-error" id="modal-error"></div>
      <div class="modal-actions">
        <button class="btn-secondary" id="modal-cancel">Cancelar</button>
        <button class="btn-modal-primary" id="modal-submit">Aceptar</button>
      </div>
    `;

    modalOverlay.innerHTML = '';
    modalOverlay.appendChild(modal);
    modalOverlay.classList.add('open');

    const firstInput = modal.querySelector('input');
    if (firstInput) setTimeout(() => firstInput.focus(), 100);

    modal.querySelector('#modal-cancel').onclick = closeModal;
    modalOverlay.onclick = (e) => { if (e.target === modalOverlay) closeModal(); };

    modal.querySelector('#modal-submit').onclick = async () => {
      const values = {};
      fields.forEach(f => {
        values[f.id] = modal.querySelector(`#modal-${f.id}`).value.trim();
      });
      const errorEl = modal.querySelector('#modal-error');
      try {
        errorEl.textContent = '';
        await onSubmit(values);
        closeModal();
      } catch (err) {
        errorEl.textContent = err.message;
      }
    };

    // Enter key submits
    modal.querySelectorAll('input').forEach(input => {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') modal.querySelector('#modal-submit').click();
      });
    });
  }

  function closeModal() {
    modalOverlay.classList.remove('open');
    modalOverlay.innerHTML = '';
  }

  // ===== Auth =====
  function initAuth() {
    authTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        authTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        loginForm.classList.toggle('hidden', target !== 'login');
        registerForm.classList.toggle('hidden', target !== 'register');
        authError.textContent = '';
      });
    });

    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      authError.textContent = '';
      const username = $('#login-username').value.trim();
      const password = $('#login-password').value;
      if (!username || !password) return;

      try {
        await api.login(username, password);
        state.currentUsername = username;
        enterChat();
      } catch (err) {
        authError.textContent = err.message;
      }
    });

    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      authError.textContent = '';
      const username = $('#register-username').value.trim();
      const password = $('#register-password').value;
      if (!username || !password) return;

      try {
        await api.register(username, password);
        state.currentUsername = username;
        enterChat();
      } catch (err) {
        authError.textContent = err.message;
      }
    });
  }

  // ===== Enter Chat View =====
  function enterChat() {
    state.currentUserId = api.getCurrentUserId();
    authView.style.display = 'none';
    chatView.style.display = 'block';
    userAvatar.textContent = (state.currentUsername || '?')[0].toUpperCase();
    usernameDisplay.textContent = state.currentUsername || 'Usuario';
    loadGroups();
  }

  // ===== Logout =====
  function logout() {
    if (state.ws) { state.ws.close(); state.ws = null; }
    api.logout();
    state.currentUserId = null;
    state.currentUsername = null;
    state.groups = [];
    state.activeGroupId = null;
    state.messages = [];
    state.members = [];
    state.usernameCache = {};
    chatView.style.display = 'none';
    authView.style.display = 'flex';
    // Clear forms
    $$('#auth-view input').forEach(i => i.value = '');
    authError.textContent = '';
    showEmptyChat();
  }

  // ===== Groups =====
  async function loadGroups() {
    try {
      const groups = await api.getGroups();
      state.groups = groups;
      renderGroups();
      
      // Select first group automatically if none active
      if (groups.length > 0 && !state.activeGroupId) {
        selectGroup(groups[0]);
      } else if (groups.length === 0) {
        showEmptyChat();
      }
    } catch (err) {
      showToast(`Error cargando grupos: ${err.message}`, 'error');
    }
  }

  function renderGroups() {
    groupsList.innerHTML = '';
    if (state.groups.length === 0) {
      groupsList.innerHTML = `
        <div class="empty-state" style="padding: 40px 20px;">
          <div class="icon">💬</div>
          <p style="font-size:13px;">No tienes grupos aún. ¡Crea uno!</p>
        </div>`;
      return;
    }

    state.groups.forEach(group => {
      const el = document.createElement('div');
      el.className = `group-item${group.id === state.activeGroupId ? ' active' : ''}`;
      el.innerHTML = `
        <div class="group-avatar">${group.name[0].toUpperCase()}</div>
        <div>
          <div class="group-name">${escapeHtml(group.name)}</div>
          <div class="group-preview">${group.id === state.activeGroupId ? 'Activo' : ''}</div>
        </div>
      `;
      el.onclick = () => selectGroup(group);
      groupsList.appendChild(el);
    });
  }

  async function createGroup() {
    openModal('Crear Grupo', [
      { id: 'name', label: 'Nombre del grupo', placeholder: 'Ej: Proyecto Telemática', minLength: 3, required: true },
    ], async (values) => {
      if (!values.name || values.name.length < 3) throw new Error('El nombre debe tener al menos 3 caracteres');
      const group = await api.createGroup(values.name);
      state.groups.push(group);
      renderGroups();
      selectGroup(group);
      showToast(`Grupo "${group.name}" creado`, 'success');
    });
  }

  async function selectGroup(group) {
    if (state.activeGroupId === group.id) return;

    // Disconnect previous WS
    if (state.ws) { state.ws.close(); state.ws = null; }

    state.activeGroupId = group.id;
    state.activeGroupData = group;
    state.messages = [];
    state.members = [];

    // Update UI
    renderGroups();
    chatGroupName.textContent = group.name;
    chatHeader.classList.remove('hidden');
    chatInputArea.classList.remove('hidden');
    emptyChat.classList.add('hidden');
    messagesContainer.classList.remove('hidden');
    messagesContainer.innerHTML = '';

    // Load messages
    try {
      const messages = await api.getMessages(group.id, 100);
      state.messages = messages;
      renderMessages();
    } catch (err) {
      showToast(`Error cargando mensajes: ${err.message}`, 'error');
    }

    // Load actual members
    try {
      const members = await api.getMembers(group.id);
      state.members = members;
      members.forEach(m => {
        state.usernameCache[m.user_id] = m.username;
      });
      if (state.membersPanelOpen) renderMembers();
    } catch (err) {
      console.warn('Error fetching members:', err.message);
    }

    // Connect WebSocket
    connectWS(group.id);

    // Update member count
    updateMemberCount();
  }

  function showEmptyChat() {
    chatHeader.classList.add('hidden');
    chatInputArea.classList.add('hidden');
    emptyChat.classList.remove('hidden');
    messagesContainer.classList.add('hidden');
    messagesContainer.innerHTML = '';
    membersPanel.classList.remove('open');
  }

  // ===== Messages =====
  function renderMessages() {
    messagesContainer.innerHTML = '';
    let lastDate = '';

    state.messages.forEach(msg => {
      const msgDateObj = parseUTCDate(msg.created_at);
      const msgDate = msgDateObj.toLocaleDateString('es-CO');
      if (msgDate !== lastDate) {
        lastDate = msgDate;
        const divider = document.createElement('div');
        divider.className = 'date-divider';
        divider.innerHTML = `<span>${msgDate}</span>`;
        messagesContainer.appendChild(divider);
      }

      const isOwn = msg.sender_id === state.currentUserId;
      const el = document.createElement('div');
      el.className = `message ${isOwn ? 'own' : 'other'}`;

      const senderName = isOwn ? 'Tú' : getSenderName(msg.sender_id);
      const time = parseUTCDate(msg.created_at).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });

      let contentHtml = '';
      if (msg.message_type === 'image') {
        contentHtml = `
          <div class="message-sender">${escapeHtml(senderName)}</div>
          ${msg.content && msg.content !== 'image' && msg.content !== 'file' ? `<div>${escapeHtml(msg.content)}</div>` : ''}
          <div class="message-image">
            <img src="${msg.file_url || '/uploads/' + encodeURIComponent(msg.content || '')}" alt="imagen" onerror="this.style.display='none'">
          </div>
        `;
      } else if (msg.message_type === 'file') {
        contentHtml = `
          <div class="message-sender">${escapeHtml(senderName)}</div>
          <div class="message-file" onclick="window.open('${msg.file_url || '/uploads/' + encodeURIComponent(msg.content || '')}', '_blank')">
            <span class="file-icon">📎</span>
            <span class="file-name">${escapeHtml(msg.content || 'Archivo')}</span>
          </div>
        `;
      } else {
        contentHtml = `
          ${!isOwn ? `<div class="message-sender">${escapeHtml(senderName)}</div>` : ''}
          <div>${escapeHtml(msg.content || '')}</div>
        `;
      }

      let receiptHtml = '';
      if (isOwn) {
        const othersReceipts = (msg.receipts || []).filter(r => r.user_id !== msg.sender_id);
        const totalOthers = othersReceipts.length;
        if (totalOthers === 0) {
          receiptHtml = `<span class="receipt-dot receipt-blue" title="Leído"></span>`;
        } else {
          const deliveredCount = othersReceipts.filter(r => r.delivered_at).length;
          const readCount = othersReceipts.filter(r => r.read_at).length;
          
          let receiptClass = 'receipt-black';
          if (readCount === totalOthers) {
            receiptClass = 'receipt-blue';
          } else if (deliveredCount === totalOthers) {
            receiptClass = 'receipt-gray';
          }
          receiptHtml = `<span class="receipt-dot ${receiptClass}" title="Ver información del mensaje"></span>`;
        }
      }

      el.innerHTML = `
        <div class="message-bubble">
          ${contentHtml}
          <div class="message-time">${time}${receiptHtml}</div>
        </div>
      `;

      if (isOwn) {
        const dot = el.querySelector('.receipt-dot');
        if (dot) dot.onclick = () => showReceiptsModal(msg);
      }

      messagesContainer.appendChild(el);
    });

    scrollToBottom();
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
  }

  function getSenderName(senderId) {
    if (state.usernameCache[senderId]) return state.usernameCache[senderId];
    // Try from members
    const member = state.members.find(m => m.user_id === senderId);
    if (member && member.username) {
      state.usernameCache[senderId] = member.username;
      return member.username;
    }
    return senderId.substring(0, 8) + '...';
  }

  async function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || !state.activeGroupId) return;

    messageInput.value = '';
    try {
      await api.sendMessage(state.activeGroupId, content);
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
      messageInput.value = content;
    }
  }

  async function uploadFile(file) {
    if (!state.activeGroupId || !file) return;
    try {
      showToast('Subiendo archivo...', 'info');
      await api.uploadFile(state.activeGroupId, file);
      showToast('Archivo enviado', 'success');
    } catch (err) {
      showToast(`Error subiendo archivo: ${err.message}`, 'error');
    }
  }

  // ===== WebSocket =====
  function connectWS(groupId) {
    state.ws = api.connectWebSocket(groupId,
      (data) => {
        // Handle incoming events
        if (data.event === 'new_message' || data.event === 'new_file') {
          const msg = data.data;
          // Avoid duplicates
          if (!state.messages.find(m => m.id === msg.id)) {
            state.messages.push(msg);
            renderMessages();
          }
        } else if (data.event === 'receipts_updated') {
          const updatedMsgs = data.data.messages || [];
          let changed = false;
          updatedMsgs.forEach(updatedMsg => {
            const index = state.messages.findIndex(m => m.id === updatedMsg.id);
            if (index !== -1) {
              state.messages[index] = updatedMsg;
              changed = true;
            }
          });
          if (changed) renderMessages();
        } else if (data.event === 'member_added') {
          if (!state.members.find(m => m.user_id === data.data.user_id)) {
            state.members.push(data.data);
            if (state.membersPanelOpen) renderMembers();
          }
        } else if (data.event === 'member_removed') {
          const removedUserId = data.data.user_id;
          if (removedUserId === state.currentUserId) {
            showToast('Has sido eliminado del grupo', 'warning');
            state.activeGroupId = null;
            emptyChat.style.display = 'flex';
            chatHeader.classList.add('hidden');
            messagesContainer.classList.add('hidden');
            chatInputArea.classList.add('hidden');
            membersPanel.classList.remove('open');
            state.membersPanelOpen = false;
            loadGroups();
          } else {
            state.members = state.members.filter(m => m.user_id !== removedUserId);
            if (state.membersPanelOpen) renderMembers();
          }
        } else if (data.event === 'member_updated') {
          const updatedUserId = data.data.user_id;
          const updatedRole = data.data.role;
          const member = state.members.find(m => m.user_id === updatedUserId);
          if (member) {
            member.role = updatedRole;
            if (state.membersPanelOpen) renderMembers();
          }
          if (updatedUserId === state.currentUserId) {
            showToast(`Tu rol ha sido actualizado a ${updatedRole}`, 'info');
          }
        }
      },
      () => {
        // On close — try reconnect after 3s if still on same group
        setTimeout(() => {
          if (state.activeGroupId === groupId && api.isAuthenticated()) {
            connectWS(groupId);
          }
        }, 3000);
      }
    );
  }

  // ===== Members =====
  function toggleMembersPanel() {
    state.membersPanelOpen = !state.membersPanelOpen;
    membersPanel.classList.toggle('open', state.membersPanelOpen);
    if (state.membersPanelOpen) {
      renderMembers();
    }
  }

  function renderMembers() {
    membersList.innerHTML = '';
    
    const activeGroup = state.groups.find(g => g.id === state.activeGroupId);
    const creatorId = activeGroup ? activeGroup.admin_id : null;
    const myMembership = state.members.find(m => m.user_id === state.currentUserId);
    const amIAdmin = myMembership && myMembership.role === 'admin';

    // Sort so admin defaults to top
    const sortedMembers = [...state.members].sort((a, b) => {
      if (a.role === 'admin' && b.role !== 'admin') return -1;
      if (b.role === 'admin' && a.role !== 'admin') return 1;
      return a.username.localeCompare(b.username);
    });

    chatMemberCount.textContent = `${sortedMembers.length} miembro${sortedMembers.length !== 1 ? 's' : ''}`;

    sortedMembers.forEach(member => {
      const isCreator = member.user_id === creatorId;
      const isAdmin = member.role === 'admin';
      const isDM = activeGroup && activeGroup.settings && activeGroup.settings.is_dm;

      let optionsHtml = '';
      if (member.user_id !== state.currentUserId) {
        let itemsHtml = '';
        if (amIAdmin && !isCreator && !isDM) {
          itemsHtml += `
            <div onclick="changeMemberRole('${member.user_id}', '${isAdmin ? 'member' : 'admin'}', event)">
              ${isAdmin ? 'Quitar Admin' : 'Hacer Admin'}
            </div>
            <div class="option-danger" onclick="expelMember('${member.user_id}', event)">
              Eliminar del grupo
            </div>
          `;
        }
        itemsHtml += `<div onclick="startDMChat('${member.user_id}', event)">Ir a chat privado</div>`;

        optionsHtml = `
          <div class="member-options" onclick="toggleMemberOptions('${member.user_id}', event)">
            ⋮
            <div class="options-dropdown" id="dropdown-${member.user_id}">
              ${itemsHtml}
            </div>
          </div>
        `;
      }

      const el = document.createElement('div');
      el.className = 'member-item';
      el.innerHTML = `
        <div class="member-avatar">
          ${(member.username || '?')[0].toUpperCase()}
          <span class="presence-dot offline" id="presence-${member.user_id}"></span>
        </div>
        <div>
          <div class="member-name">${escapeHtml(member.username)}</div>
          <div class="member-role ${member.role}">${member.role === 'admin' && !isDM ? '👑 Admin' : 'Miembro'}</div>
        </div>
        ${optionsHtml}
      `;
      // Don't toggle options if clicking on empty space
      el.onclick = (e) => {
        if (!e.target.closest('.member-options')) {
          checkPresence(member.user_id);
        }
      };
      membersList.appendChild(el);

      // Fetch presence
      fetchPresence(member.user_id);
    });
  }

  // ===== Member Options UI =====
  window.toggleMemberOptions = function(userId, event) {
    event.stopPropagation();
    document.querySelectorAll('.options-dropdown').forEach(el => {
      if(el.id !== `dropdown-${userId}`) el.classList.remove('show');
    });
    const dropdown = document.getElementById(`dropdown-${userId}`);
    if (dropdown) dropdown.classList.toggle('show');
  };

  document.addEventListener('click', () => {
    document.querySelectorAll('.options-dropdown.show').forEach(el => el.classList.remove('show'));
  });

  window.changeMemberRole = async function(userId, newRole, event) {
    event.stopPropagation();
    document.querySelectorAll('.options-dropdown.show').forEach(el => el.classList.remove('show'));
    try {
      if(newRole === 'admin' && !confirm('¿Estás seguro de hacer a este usuario Administrador?')) return;
      await api.updateMemberRole(state.activeGroupId, userId, newRole);
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
    }
  };

  window.expelMember = async function(userId, event) {
    event.stopPropagation();
    document.querySelectorAll('.options-dropdown.show').forEach(el => el.classList.remove('show'));
    if (!confirm('¿Estás seguro de que deseas eliminar a este integrante del grupo?')) return;
    try {
      await api.removeMember(state.activeGroupId, userId);
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
    }
  };

  window.startDMChat = async function(userId, event) {
    if (event) event.stopPropagation();
    document.querySelectorAll('.options-dropdown.show').forEach(el => el.classList.remove('show'));
    try {
      const dmGroup = await api.startDM(userId);
      if (!state.groups.find(g => g.id === dmGroup.id)) {
        state.groups.unshift(dmGroup); 
      }
      selectGroup(dmGroup);
      if (state.membersPanelOpen) toggleMembersPanel();
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
    }
  };

  async function fetchPresence(userId) {
    try {
      const presence = await api.getPresence(userId);
      const dot = document.getElementById(`presence-${userId}`);
      if (dot) {
        dot.className = `presence-dot ${presence.is_online ? 'online' : 'offline'}`;
      }
    } catch {
      // Ignore — user may not have presence record yet
    }
  }

  async function checkPresence(userId) {
    try {
      const presence = await api.getPresence(userId);
      const status = presence.is_online ? '🟢 En línea' : '⚫ Desconectado';
      const lastSeen = presence.last_seen
        ? `Última vez: ${parseUTCDate(presence.last_seen).toLocaleString('es-CO')}`
        : '';
      showToast(`${status} ${lastSeen}`, 'info');
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
    }
  }

  function updateMemberCount() {
    chatMemberCount.textContent = `${state.members.length} miembro${state.members.length !== 1 ? 's' : ''}`;
  }

  async function addMember() {
    if (!state.activeGroupId) return;
    openModal('Agregar Miembro', [
      { id: 'username', label: 'Username del usuario', placeholder: 'Ej: juanda', required: true },
    ], async (values) => {
      if (!values.username) throw new Error('Ingresa un username');
      await api.addMember(state.activeGroupId, values.username);
      showToast(`${values.username} agregado al grupo`, 'success');
      // Add to cache
      if (state.membersPanelOpen) renderMembers();
    });
  }

  // ===== Utilities =====
  function parseUTCDate(dateStr) {
    if (!dateStr) return null;
    let str = String(dateStr);
    // Replace space with T just in case
    str = str.replace(' ', 'T');
    // If it doesn't have Z or timezone offset, force append Z to make it UTC
    if (!str.endsWith('Z') && !str.includes('+') && (str.split('-').length <= 3)) {
      str += 'Z';
    }
    return new Date(str);
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ===== Receipts Modal =====
  function showReceiptsModal(msg) {
    const othersReceipts = (msg.receipts || []).filter(r => r.user_id !== msg.sender_id);
    if (othersReceipts.length === 0) {
      showToast("No hay otros miembros en el grupo", "info");
      return;
    }
    
    // Sort logic
    const sorted = [...othersReceipts].sort((a, b) => {
      if (a.read_at && !b.read_at) return -1;
      if (!a.read_at && b.read_at) return 1;
      if (a.delivered_at && !b.delivered_at) return -1;
      if (!a.delivered_at && b.delivered_at) return 1;
      return 0;
    });

    const receiptsHtml = sorted.map(r => {
      const username = getSenderName(r.user_id);
      let statusHtml = '';
      if (r.read_at) {
        const time = parseUTCDate(r.read_at).toLocaleString('es-CO', {day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'});
        statusHtml = `<span class="receipt-tag tag-read">Visto: ${time}</span>`;
      } else if (r.delivered_at) {
        const time = parseUTCDate(r.delivered_at).toLocaleString('es-CO', {day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'});
        statusHtml = `<span class="receipt-tag tag-delivered">Entregado: ${time}</span>`;
      } else {
        statusHtml = `<span class="receipt-tag tag-pending">Pendiente</span>`;
      }
      return `
        <div class="receipt-user">
          <div>${escapeHtml(username)}</div>
          <div class="receipt-status">${statusHtml}</div>
        </div>
      `;
    }).join('');

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <h3>Información del mensaje</h3>
      <div class="receipts-list">
        ${receiptsHtml}
      </div>
      <div class="modal-actions">
        <button class="btn-modal-primary" id="modal-close">Cerrar</button>
      </div>
    `;

    modalOverlay.innerHTML = '';
    modalOverlay.appendChild(modal);
    modalOverlay.classList.add('open');

    modal.querySelector('#modal-close').onclick = closeModal;
    modalOverlay.onclick = (e) => { if (e.target === modalOverlay) closeModal(); };
  }

  // ===== Event Listeners =====
  function initEventListeners() {
    // Logout
    $('#btn-logout').onclick = logout;

    // New Group
    $('#btn-new-group').onclick = createGroup;

    // Send message
    btnSend.onclick = sendMessage;
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // File upload
    btnAttach.onclick = () => fileInput.click();
    fileInput.onchange = (e) => {
      const file = e.target.files[0];
      if (file) uploadFile(file);
      fileInput.value = '';
    };

    // Members panel
    btnMembers.onclick = toggleMembersPanel;

    // Add member
    $('#btn-add-member').onclick = addMember;

    // Leave chat
    if (btnLeave) {
      btnLeave.onclick = async () => {
        if (!state.activeGroupId) return;
        if (!confirm('¿Estás seguro de que deseas abandonar este chat?')) return;
        try {
          await api.removeMember(state.activeGroupId, state.currentUserId);
        } catch (err) {
          showToast(`Error: ${err.message}`, 'error');
        }
      };
    }
  }

  // ===== Init =====
  function init() {
    initAuth();
    initEventListeners();

    // Check if already authenticated
    if (api.isAuthenticated()) {
      // Try to recover username from storage
      state.currentUsername = localStorage.getItem('username') || 'Usuario';
      enterChat();
    }
  }

  // Store username on auth
  const origSetToken = api.setToken.bind(api);
  api.setToken = function(token) {
    origSetToken(token);
  };

  // Patch login/register to save username
  const origLogin = api.login.bind(api);
  api.login = async function(username, password) {
    const result = await origLogin(username, password);
    localStorage.setItem('username', username);
    return result;
  };

  const origRegister = api.register.bind(api);
  api.register = async function(username, password) {
    const result = await origRegister(username, password);
    localStorage.setItem('username', username);
    return result;
  };

  // ===== Start =====
  document.addEventListener('DOMContentLoaded', init);
})();
