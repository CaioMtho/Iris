// chatbot.js — versão limpa e estável
class IrisChatbot {
  constructor() {
    this.messagesContainer = document.getElementById('chat-messages');
    this.chatForm = document.getElementById('chat-form');
    this.chatInput = document.getElementById('chat-input');
    this.sendBtn = document.getElementById('send-btn');
    this.typingIndicator = document.getElementById('typing-indicator');
    this.quickSuggestions = document.getElementById('quick-suggestions');
    this.charCount = document.getElementById('char-count');
    this.messagesCount = document.getElementById('messages-count');
    this.sessionTime = document.getElementById('session-time');
    this.sessionTimerInterval = null;

    this.messageHistory = [];
    this.sessionStartTime = Date.now();
    this.messageCounter = 1;
    this.sessionId = null;

    // flag simples para debug — remova se quiser
    console.log('chatbot.js loaded — stable');

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupAutoResize();
    this.startSessionTimer();
    this.loadChatHistory();
  }

  setupEventListeners() {
    if (this.chatForm) {
      this.chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.sendMessage();
      });
    }

    if (this.chatInput) {
      this.chatInput.addEventListener('input', () => {
        this.updateCharCount();
        this.toggleSendButton();
        this.autoResizeTextarea();
      });

      this.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          if (this.chatInput.value.trim()) {
            this.sendMessage();
          }
        }
      });
    }

    if (this.quickSuggestions) {
      this.quickSuggestions.addEventListener('click', (e) => {
        const btn = e.target;
        if (btn && btn.classList && btn.classList.contains('suggestion-btn')) {
          const suggestion = btn.dataset && btn.dataset.suggestion;
          if (this.chatInput && typeof suggestion === 'string') {
            this.chatInput.value = suggestion;
            this.updateCharCount();
            this.toggleSendButton();
            this.chatInput.focus();
          }
        }
      });
    }

    const clearBtn = document.getElementById('clear-chat');
    if (clearBtn) clearBtn.addEventListener('click', () => this.clearChat());

    const exportBtn = document.getElementById('export-chat');
    if (exportBtn) exportBtn.addEventListener('click', () => this.exportChat());

    const autoScrollEl = document.getElementById('auto-scroll');
    if (autoScrollEl) autoScrollEl.addEventListener('change', (e) => {
      this.autoScroll = !!e.target.checked;
    });

    const saveHistoryEl = document.getElementById('save-history');
    if (saveHistoryEl) saveHistoryEl.addEventListener('change', (e) => {
      this.saveHistory = !!e.target.checked;
      if (!this.saveHistory) localStorage.removeItem('iris_chat_history');
    });
  }

  setupAutoResize() {
    this.autoResizeTextarea();
  }

  autoResizeTextarea() {
    if (!this.chatInput) return;
    this.chatInput.style.height = 'auto';
    this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
  }

  updateCharCount() {
    if (!this.charCount || !this.chatInput) return;
    const count = this.chatInput.value.length;
    this.charCount.textContent = String(count);

    if (count > 800) {
      this.charCount.style.color = 'var(--accent-red, #ef4444)';
    } else if (count > 600) {
      this.charCount.style.color = 'var(--secondary-yellow)';
    } else {
      this.charCount.style.color = 'var(--neutral-700)';
    }
  }

  toggleSendButton() {
    if (!this.sendBtn || !this.chatInput) return;
    const hasText = this.chatInput.value.trim().length > 0;
    this.sendBtn.disabled = !hasText;
  }

  async sendMessage() {
    if (!this.chatInput) return;
    const message = this.chatInput.value.trim();
    if (!message) return;

    this.addMessage(message, 'user');

    this.chatInput.value = '';
    this.updateCharCount();
    this.toggleSendButton();
    this.autoResizeTextarea();

    if (this.quickSuggestions) this.quickSuggestions.style.display = 'none';
    this.showTypingIndicator();

    try {
      const response = await this.sendToAPI(message);
      this.hideTypingIndicator();
      this.addMessage(response, 'bot');
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      this.hideTypingIndicator();
      const errorMessage = this.getErrorMessage(error);
      this.addMessage(errorMessage, 'bot', true);
    }
  }

  async sendToAPI(message) {
    const API_ENDPOINT = '/api/v1/chat/';
    const requestBody = {
      message: message,
      session_id: this.getSessionId(),
      user_id: this.getUserId(),
      max_tokens: 512,
      temperature: 0.0
    };

    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.session_id) this.saveSessionId(data.session_id);
    return data.response || data.message || 'Desculpe, não consegui processar sua mensagem.';
  }

  getSessionId() {
    if (!this.sessionId) {
      this.sessionId = this.sessionIdMemory || ('session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9));
      this.sessionIdMemory = this.sessionId;
    }
    return this.sessionId;
  }

  saveSessionId(sessionId) {
    this.sessionId = sessionId;
    this.sessionIdMemory = sessionId;
  }

  getUserId() {
    let userId = localStorage.getItem('iris_user_id');
    if (!userId) {
      userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      try { localStorage.setItem('iris_user_id', userId); } catch (e) { /* ignore */ }
    }
    return userId;
  }

  addMessage(content, type, isError = false) {
    if (!this.messagesContainer) return;

    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}-message`;

    const avatarIcon = type === 'user' ? '👤' : '🤖';
    const timestamp = this.formatTime(new Date());

    messageElement.innerHTML = `
      <div class="message-avatar">
        <div class="avatar-icon">${avatarIcon}</div>
      </div>
      <div class="message-content">
        <div class="message-bubble ${isError ? 'error' : ''}">
          ${this.formatMessageContent(content)}
        </div>
        <div class="message-time">${timestamp}</div>
      </div>
    `;

    if (this.typingIndicator && this.typingIndicator.parentNode === this.messagesContainer) {
      this.messagesContainer.insertBefore(messageElement, this.typingIndicator);
    } else {
      this.messagesContainer.appendChild(messageElement);
    }

    this.messageHistory.push({ content, type, timestamp: Date.now(), isError });

    this.messageCounter++;
    if (this.messagesCount) this.messagesCount.textContent = String(this.messageCounter);

    const autoScrollEl = document.getElementById('auto-scroll');
    if (autoScrollEl && autoScrollEl.checked) this.scrollToBottom();

    const saveHistoryEl = document.getElementById('save-history');
    if (saveHistoryEl && saveHistoryEl.checked) this.saveChatHistory();
  }

  formatMessageContent(content) {
    if (!content) return '';
    content = String(content).replace(/\n/g, '<br>');
    content = content.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    content = content.replace(/@([a-zA-ZÀ-ÿ\s]+)/g, '<span class="mention">@$1</span>');
    content = content.replace(/#([a-zA-ZÀ-ÿ0-9_]+)/g, '<span class="hashtag">#$1</span>');
    return content;
  }

  formatTime(date) {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  showTypingIndicator() {
    if (!this.typingIndicator) return;
    this.typingIndicator.style.display = 'block';
    this.scrollToBottom();
  }

  hideTypingIndicator() {
    if (!this.typingIndicator) return;
    this.typingIndicator.style.display = 'none';
  }

  scrollToBottom() {
    if (!this.messagesContainer) return;
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  getErrorMessage(error) {
    const errorMsg = (error && error.message) ? String(error.message).toLowerCase() : String(error).toLowerCase();
    if (errorMsg.includes('failed to fetch') || errorMsg.includes('networkerror')) {
      return 'Desculpe, não consegui me conectar ao servidor. Verifique sua conexão com a internet e tente novamente.';
    } else if (errorMsg.includes('500')) {
      return 'Ops! Estou com alguns problemas técnicos no momento. Tente novamente em alguns instantes.';
    } else if (errorMsg.includes('429')) {
      return 'Você está enviando muitas mensagens muito rapidamente. Aguarde um momento antes de tentar novamente.';
    } else if (errorMsg.includes('404')) {
      return 'Serviço de chat temporariamente indisponível. Por favor, tente novamente mais tarde.';
    } else if (errorMsg.includes('401') || errorMsg.includes('403')) {
      return 'Erro de autenticação. Por favor, recarregue a página e tente novamente.';
    } else {
      return 'Desculpe, ocorreu um erro inesperado. Tente reformular sua pergunta ou entre em contato com o suporte.';
    }
  }

  clearChat() {
    if (!this.messagesContainer) return;
    if (!confirm('Tem certeza que deseja limpar toda a conversa?')) return;

    const welcomeMessage = this.messagesContainer.querySelector('.bot-message');
    const quickSuggestions = this.quickSuggestions;
    const typingIndicator = this.typingIndicator;

    this.messagesContainer.innerHTML = '';

    if (welcomeMessage) this.messagesContainer.appendChild(welcomeMessage);
    if (quickSuggestions) { this.messagesContainer.appendChild(quickSuggestions); quickSuggestions.style.display = 'block'; }
    if (typingIndicator) this.messagesContainer.appendChild(typingIndicator);

    this.messageHistory = [];
    this.messageCounter = 1;
    if (this.messagesCount) this.messagesCount.textContent = '1';

    this.stopSessionTimer();
    if (this.sessionTime) this.sessionTime.textContent = '0s';

    this.sessionId = null;
    this.sessionIdMemory = null;

    localStorage.removeItem('iris_chat_history');
    if (typeof mostrarSucesso === 'function') mostrarSucesso('Conversa limpa com sucesso!');
  }

  exportChat() {
    if (this.messageHistory.length === 0) {
      if (typeof mostrarErro === 'function') mostrarErro('Não há mensagens para exportar.');
      return;
    }
    const chatData = {
      timestamp: new Date().toISOString(),
      session_duration: this.getSessionDuration(),
      session_id: this.sessionId,
      user_id: this.getUserId(),
      messages: this.messageHistory.map(msg => ({ content: msg.content, type: msg.type, time: new Date(msg.timestamp).toLocaleString('pt-BR') }))
    };
    const dataStr = JSON.stringify(chatData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `iris_chat_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    if (typeof mostrarSucesso === 'function') mostrarSucesso('Conversa exportada com sucesso!');
  }

  saveChatHistory() {
    try { localStorage.setItem('iris_chat_history', JSON.stringify(this.messageHistory)); } catch (e) { console.warn(e); }
  }

  loadChatHistory() {
    try {
      const saved = localStorage.getItem('iris_chat_history');
      const saveHistoryEl = document.getElementById('save-history');
      if (saved && saveHistoryEl && saveHistoryEl.checked) {
        this.messageHistory = JSON.parse(saved);
      }
    } catch (e) { console.warn(e); }
  }

  startSessionTimer() {
    // limpa intervalo anterior
    if (this.sessionTimerInterval) {
      clearInterval(this.sessionTimerInterval);
      this.sessionTimerInterval = null;
    }

    // escreve imediatamente se possível
    const el = document.getElementById('session-time') || this.sessionTime;
    if (el) {
      try { el.textContent = this.getSessionDuration(); } catch (_) {}
      this.sessionTime = el;
    }

    // cria intervalo que apenas tenta atualizar se o elemento existir
    this.sessionTimerInterval = setInterval(() => {
      const nowEl = document.getElementById('session-time') || this.sessionTime;
      if (nowEl) {
        try { nowEl.textContent = this.getSessionDuration(); } catch (_) {}
        this.sessionTime = nowEl;
      }
    }, 1000);
  }

  stopSessionTimer() {
    if (this.sessionTimerInterval) {
      clearInterval(this.sessionTimerInterval);
      this.sessionTimerInterval = null;
    }
  }

  getSessionDuration() {
    const elapsed = Date.now() - this.sessionStartTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
  }
}

// inicializar quando DOM pronto
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('chat-messages')) {
    window.irisChatbot = new IrisChatbot();
  }
});
