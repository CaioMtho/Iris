// Chatbot JavaScript - Iris
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
    
    this.messageHistory = [];
    this.sessionStartTime = Date.now();
    this.messageCounter = 1; // Começar com 1 por causa da mensagem de boas-vindas
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupAutoResize();
    this.startSessionTimer();
    this.loadChatHistory();
  }

  setupEventListeners() {
    // Envio de mensagem
    this.chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      this.sendMessage();
    });

    // Auto-resize do textarea
    this.chatInput.addEventListener('input', () => {
      this.updateCharCount();
      this.toggleSendButton();
      this.autoResizeTextarea();
    });

    // Envio com Enter (sem Shift)
    this.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (this.chatInput.value.trim()) {
          this.sendMessage();
        }
      }
    });

    // Sugestões rápidas
    this.quickSuggestions.addEventListener('click', (e) => {
      if (e.target.classList.contains('suggestion-btn')) {
        const suggestion = e.target.dataset.suggestion;
        this.chatInput.value = suggestion;
        this.updateCharCount();
        this.toggleSendButton();
        this.chatInput.focus();
      }
    });

    // Botões de ação
    document.getElementById('clear-chat').addEventListener('click', () => {
      this.clearChat();
    });

    document.getElementById('export-chat').addEventListener('click', () => {
      this.exportChat();
    });

    // Configurações
    document.getElementById('auto-scroll').addEventListener('change', (e) => {
      this.autoScroll = e.target.checked;
    });

    document.getElementById('save-history').addEventListener('change', (e) => {
      this.saveHistory = e.target.checked;
      if (!this.saveHistory) {
        localStorage.removeItem('iris_chat_history');
      }
    });
  }

  setupAutoResize() {
    this.autoResizeTextarea();
  }

  autoResizeTextarea() {
    this.chatInput.style.height = 'auto';
    this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
  }

  updateCharCount() {
    const count = this.chatInput.value.length;
    this.charCount.textContent = count;
    
    if (count > 800) {
      this.charCount.style.color = 'var(--accent-red, #ef4444)';
    } else if (count > 600) {
      this.charCount.style.color = 'var(--secondary-yellow)';
    } else {
      this.charCount.style.color = 'var(--neutral-700)';
    }
  }

  toggleSendButton() {
    const hasText = this.chatInput.value.trim().length > 0;
    this.sendBtn.disabled = !hasText;
  }

  async sendMessage() {
    const message = this.chatInput.value.trim();
    if (!message) return;

    // Adicionar mensagem do usuário
    this.addMessage(message, 'user');
    
    // Limpar input
    this.chatInput.value = '';
    this.updateCharCount();
    this.toggleSendButton();
    this.autoResizeTextarea();

    // Esconder sugestões após primeira mensagem
    if (this.quickSuggestions) {
      this.quickSuggestions.style.display = 'none';
    }

    // Mostrar indicador de digitação
    this.showTypingIndicator();

    try {
      // Enviar para a API do chatbot
      const response = await this.sendToAPI(message);
      
      // Esconder indicador de digitação
      this.hideTypingIndicator();
      
      // Adicionar resposta do bot
      this.addMessage(response, 'bot');
      
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      this.hideTypingIndicator();
      
      // Mensagem de erro amigável
      const errorMessage = this.getErrorMessage(error);
      this.addMessage(errorMessage, 'bot', true);
    }
  }

  async sendToAPI(message) {
    // Configuração da API do chatbot (Llama 3.2:3b)
    const API_ENDPOINT = '/api/v1/chatbot/chat'; // Endpoint que você criará no backend
    
    const requestBody = {
      message: message,
      context: this.getConversationContext(),
      user_id: this.getUserId(),
      timestamp: new Date().toISOString()
    };

    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data.response || data.message || 'Desculpe, não consegui processar sua mensagem.';
  }

  getConversationContext() {
    // Retorna as últimas 5 mensagens para contexto
    return this.messageHistory.slice(-10).map(msg => ({
      role: msg.type === 'user' ? 'user' : 'assistant',
      content: msg.content
    }));
  }

  getUserId() {
    // Gerar ou recuperar ID único do usuário
    let userId = localStorage.getItem('iris_user_id');
    if (!userId) {
      userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('iris_user_id', userId);
    }
    return userId;
  }

  addMessage(content, type, isError = false) {
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

    // Inserir antes do indicador de digitação
    this.messagesContainer.insertBefore(messageElement, this.typingIndicator);
    
    // Salvar no histórico
    this.messageHistory.push({
      content: content,
      type: type,
      timestamp: Date.now(),
      isError: isError
    });

    // Atualizar contador
    this.messageCounter++;
    this.messagesCount.textContent = this.messageCounter;

    // Auto-scroll
    if (document.getElementById('auto-scroll').checked) {
      this.scrollToBottom();
    }

    // Salvar histórico
    if (document.getElementById('save-history').checked) {
      this.saveChatHistory();
    }
  }

  formatMessageContent(content) {
    // Converter quebras de linha em <br>
    content = content.replace(/\n/g, '<br>');
    
    // Detectar e formatar links
    content = content.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    
    // Detectar menções a políticos (formato @nome)
    content = content.replace(/@([a-zA-ZÀ-ÿ\s]+)/g, '<span class="mention">@$1</span>');
    
    // Detectar hashtags
    content = content.replace(/#([a-zA-ZÀ-ÿ0-9_]+)/g, '<span class="hashtag">#$1</span>');
    
    return content;
  }

  formatTime(date) {
    return date.toLocaleTimeString('pt-BR', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  showTypingIndicator() {
    this.typingIndicator.style.display = 'block';
    this.scrollToBottom();
  }

  hideTypingIndicator() {
    this.typingIndicator.style.display = 'none';
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  getErrorMessage(error) {
    if (error.message.includes('Failed to fetch')) {
      return 'Desculpe, não consegui me conectar ao servidor. Verifique sua conexão com a internet e tente novamente.';
    } else if (error.message.includes('500')) {
      return 'Ops! Estou com alguns problemas técnicos no momento. Tente novamente em alguns instantes.';
    } else if (error.message.includes('429')) {
      return 'Você está enviando muitas mensagens muito rapidamente. Aguarde um momento antes de tentar novamente.';
    } else {
      return 'Desculpe, ocorreu um erro inesperado. Tente reformular sua pergunta ou entre em contato com o suporte.';
    }
  }

  clearChat() {
    if (confirm('Tem certeza que deseja limpar toda a conversa?')) {
      // Manter apenas a mensagem de boas-vindas
      const welcomeMessage = this.messagesContainer.querySelector('.message');
      this.messagesContainer.innerHTML = '';
      this.messagesContainer.appendChild(welcomeMessage);
      this.messagesContainer.appendChild(this.quickSuggestions);
      this.messagesContainer.appendChild(this.typingIndicator);
      
      // Resetar dados
      this.messageHistory = [];
      this.messageCounter = 1;
      this.messagesCount.textContent = '1';
      
      // Mostrar sugestões novamente
      this.quickSuggestions.style.display = 'block';
      
      // Limpar histórico salvo
      localStorage.removeItem('iris_chat_history');
      
      mostrarSucesso('Conversa limpa com sucesso!');
    }
  }

  exportChat() {
    if (this.messageHistory.length === 0) {
      mostrarErro('Não há mensagens para exportar.');
      return;
    }

    const chatData = {
      timestamp: new Date().toISOString(),
      session_duration: this.getSessionDuration(),
      messages: this.messageHistory.map(msg => ({
        content: msg.content,
        type: msg.type,
        time: new Date(msg.timestamp).toLocaleString('pt-BR')
      }))
    };

    const dataStr = JSON.stringify(chatData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `iris_chat_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    mostrarSucesso('Conversa exportada com sucesso!');
  }

  saveChatHistory() {
    try {
      localStorage.setItem('iris_chat_history', JSON.stringify(this.messageHistory));
    } catch (error) {
      console.warn('Não foi possível salvar o histórico:', error);
    }
  }

  loadChatHistory() {
    try {
      const saved = localStorage.getItem('iris_chat_history');
      if (saved && document.getElementById('save-history').checked) {
        this.messageHistory = JSON.parse(saved);
        
        // Recriar mensagens salvas (opcional - pode ser muito para UX)
        // this.recreateSavedMessages();
      }
    } catch (error) {
      console.warn('Não foi possível carregar o histórico:', error);
    }
  }

  startSessionTimer() {
    setInterval(() => {
      const duration = this.getSessionDuration();
      this.sessionTime.textContent = duration;
    }, 1000);
  }

  getSessionDuration() {
    const elapsed = Date.now() - this.sessionStartTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  }
}

// Inicializar chatbot quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
  // Verificar se estamos na página do chatbot
  if (document.getElementById('chat-messages')) {
    window.irisChatbot = new IrisChatbot();
  }
});

// Adicionar estilos CSS adicionais via JavaScript
const additionalStyles = `
  .message-bubble.error {
    background: #fee2e2 !important;
    border: 1px solid #fca5a5 !important;
    color: #dc2626 !important;
  }
  
  .mention {
    background: var(--primary-green);
    color: white;
    padding: 0.1rem 0.3rem;
    border-radius: 0.25rem;
    font-weight: 500;
  }
  
  .hashtag {
    color: var(--accent-blue);
    font-weight: 500;
  }
  
  .message-bubble a {
    color: var(--accent-blue);
    text-decoration: underline;
  }
  
  .message-bubble a:hover {
    text-decoration: none;
  }
`;

// Adicionar estilos ao head
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

