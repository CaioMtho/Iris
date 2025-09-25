const API_BASE_URL = window.location.origin + '/api/v1';

// Classe para gerenciar comunicação com a API
class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  // Método genérico para fazer requisições
  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      if (response.status === 204) {
        return null;
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Erro na requisição para ${url}:`, error);
      throw error;
    }
  }

  // ========== ENDPOINTS DE POLÍTICOS ==========

  async listarPoliticos() {
    return this.makeRequest('/politicos/');
  }

  async buscarPolitico(id) {
    return this.makeRequest(`/politicos/${id}`);
  }

  async criarPolitico(dadosPolitico) {
    return this.makeRequest('/politicos/', {
      method: 'POST',
      body: JSON.stringify(dadosPolitico)
    });
  }

  async atualizarPolitico(id, dadosPolitico) {
    return this.makeRequest(`/politicos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(dadosPolitico)
    });
  }

  async upsertPolitico(id, dadosPolitico) {
    return this.makeRequest(`/politicos/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(dadosPolitico)
    });
  }

  async deletarPolitico(id) {
    return this.makeRequest(`/politicos/${id}`, {
      method: 'DELETE'
    });
  }

  async listarPoliticosPorPartido(partido) {
    return this.makeRequest(`/politicos/partido/${encodeURIComponent(partido)}`);
  }

  // ========== ENDPOINTS DE PROTÓTIPO ==========

  async obterVotacoesPrototipo() {
    return this.makeRequest('/prototipo');
  }

  async calcularAfinidade(dadosQuestionario) {
    this.validarDadosQuestionario(dadosQuestionario);
    
    return this.makeRequest('/prototipo/calcular-afinidade', {
      method: 'POST',
      body: JSON.stringify(dadosQuestionario)
    });
  }

  // ========== VALIDAÇÕES ==========

  validarDadosQuestionario(dados) {
    if (!dados) {
      throw new Error('Dados do questionário são obrigatórios.');
    }

    if (!dados.nome_usuario || !dados.nome_usuario.trim()) {
      throw new Error('Nome do usuário é obrigatório.');
    }

    if (!dados.votos || !Array.isArray(dados.votos) || dados.votos.length === 0) {
      throw new Error('Votos são obrigatórios.');
    }

    const votosValidos = ['SIM', 'NAO', 'ABSTENCAO'];
    dados.votos.forEach((voto, index) => {
      if (!voto.votacao_id) {
        throw new Error(`Voto ${index + 1}: ID da votação é obrigatório.`);
      }

      if (!votosValidos.includes(voto.voto)) {
        throw new Error(`Voto ${index + 1}: Voto inválido. Valores aceitos: ${votosValidos.join(', ')}`);
      }
    });

    return true;
  }

  // ========== MÉTODOS UTILITÁRIOS ==========

  async buscarPoliticosComFiltros(filtros = {}) {
    let politicos = await this.listarPoliticos();
    
    if (filtros.nome) {
      const nome = filtros.nome.toLowerCase();
      politicos = politicos.filter(p => 
        p.nome.toLowerCase().includes(nome)
      );
    }
    
    if (filtros.partido) {
      politicos = politicos.filter(p => 
        p.partido === filtros.partido
      );
    }
    
    if (filtros.estado) {
      politicos = politicos.filter(p => 
        p.uf === filtros.estado
      );
    }
    
    return politicos;
  }

  async obterPartidos() {
    const politicos = await this.listarPoliticos();
    const partidos = [...new Set(politicos.map(p => p.partido))];
    return partidos.sort();
  }

  async obterEstados() {
    const politicos = await this.listarPoliticos();
    const estados = [...new Set(politicos.map(p => p.uf))];
    return estados.sort();
  }

  async obterEstatisticas() {
    try {
      const [politicos, votacoes] = await Promise.all([
        this.listarPoliticos(),
        this.obterVotacoesPrototipo()
      ]);

      const partidos = new Set(politicos.map(p => p.partido));
      const estados = new Set(politicos.map(p => p.uf));

      return {
        totalPoliticos: politicos.length,
        totalPartidos: partidos.size,
        totalEstados: estados.size,
        totalVotacoes: votacoes?.votacoes?.length || 0
      };
    } catch (error) {
      console.error('Erro ao obter estatísticas:', error);
      return {
        totalPoliticos: 0,
        totalPartidos: 0,
        totalEstados: 0,
        totalVotacoes: 0
      };
    }
  }

  // ========== MÉTODOS DE CACHE ==========

  _cacheVotacoes = null;
  _timestampCache = null;
  _tempoExpiracaoCache = 5 * 60 * 1000; // 5 minutos

  async obterVotacoesPrototipoComCache() {
    const agora = Date.now();
    
    if (this._cacheVotacoes && 
        this._timestampCache && 
        (agora - this._timestampCache) < this._tempoExpiracaoCache) {
      console.log('Usando votações do cache');
      return this._cacheVotacoes;
    }

    console.log('Buscando votações da API');
    const votacoes = await this.obterVotacoesPrototipo();
    
    this._cacheVotacoes = votacoes;
    this._timestampCache = agora;
    
    return votacoes;
  }

  limparCache() {
    this._cacheVotacoes = null;
    this._timestampCache = null;
  }

  // ========== MÉTODOS DE RETRY ==========

  // Fazer requisição com retry automático
  async makeRequestWithRetry(endpoint, options = {}, maxRetries = 3) {
    let lastError;
    
    for (let tentativa = 0; tentativa < maxRetries; tentativa++) {
      try {
        return await this.makeRequest(endpoint, options);
      } catch (error) {
        lastError = error;
        
        if (!error.message.includes('Failed to fetch') && 
            !error.message.includes('NetworkError')) {
          throw error;
        }
        
        if (tentativa < maxRetries - 1) {
          await this.sleep(1000 * (tentativa + 1));
          console.log(`Tentativa ${tentativa + 2}/${maxRetries} para ${endpoint}`);
        }
      }
    }
    
    throw lastError;
  }

  async calcularAfinidadeComRetry(dadosQuestionario) {
    return this.makeRequestWithRetry('/prototipo/calcular-afinidade', {
      method: 'POST',
      body: JSON.stringify(dadosQuestionario)
    });
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Instância global da API
const api = new ApiService();

// ========== FUNÇÕES UTILITÁRIAS ==========

// Funções utilitárias para tratamento de erros
function mostrarErro(mensagem) {
  console.error(mensagem);
  
  const notification = document.createElement('div');
  notification.className = 'notification error';
  notification.innerHTML = `
    <div class="notification-content">
      <span class="notification-icon">⚠️</span>
      <span class="notification-message">${mensagem}</span>
      <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
  `;
  
  let container = document.querySelector('.notifications-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notifications-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      max-width: 400px;
    `;
    document.body.appendChild(container);
  }
  
  container.appendChild(notification);
  
  // Remover automaticamente após 5 segundos
  setTimeout(() => {
    if (notification.parentElement) {
      notification.remove();
    }
  }, 5000);
}

function mostrarSucesso(mensagem) {
  console.log(mensagem);
  
  const notification = document.createElement('div');
  notification.className = 'notification success';
  notification.innerHTML = `
    <div class="notification-content">
      <span class="notification-icon">✅</span>
      <span class="notification-message">${mensagem}</span>
      <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
  `;
  
  let container = document.querySelector('.notifications-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notifications-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      max-width: 400px;
    `;
    document.body.appendChild(container);
  }
  
  container.appendChild(notification);
  
  setTimeout(() => {
    if (notification.parentElement) {
      notification.remove();
    }
  }, 3000);
}

// Função para mostrar loading
function mostrarLoading(elemento) {
  if (elemento) {
    elemento.innerHTML = `
      <div class="loading">
        <div class="spinner"></div>
        <p>Carregando...</p>
      </div>
    `;
  }
}

// Função para esconder loading
function esconderLoading(elemento) {
  if (elemento) {
    const loading = elemento.querySelector('.loading');
    if (loading) {
      loading.remove();
    }
  }
}

function formatarPolitico(politico) {
  return {
    ...politico,
    nomeFormatado: politico.nome || 'Nome não informado',
    partidoFormatado: politico.partido || 'Partido não informado',
    estadoFormatado: politico.uf || 'Estado não informado',
    cargoFormatado: politico.cargo || 'Cargo não informado'
  };
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function formatarPorcentagem(valor, decimais = 1) {
  return `${valor.toFixed(decimais)}%`;
}

function formatarData(data) {
  return new Date(data).toLocaleDateString('pt-BR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// Estilos CSS para notificações
const notificationStyles = `
  .notifications-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    max-width: 400px;
    pointer-events: none;
  }

  .notification {
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    margin-bottom: 1rem;
    overflow: hidden;
    animation: slideInRight 0.3s ease-out;
    pointer-events: auto;
  }

  .notification.error {
    border-left: 4px solid #ef4444;
  }

  .notification.success {
    border-left: 4px solid #22c55e;
  }

  .notification-content {
    padding: 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .notification-icon {
    font-size: 1.25rem;
  }

  .notification-message {
    flex: 1;
    font-size: 0.9rem;
    color: #374151;
  }

  .notification-close {
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    color: #9ca3af;
    padding: 0.25rem;
  }

  .notification-close:hover {
    color: #374151;
  }

  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    text-align: center;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #e5e7eb;
    border-top: 4px solid var(--primary-green, #047857);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

// Adicionar estilos ao documento
if (!document.getElementById('notification-styles')) {
  const styleSheet = document.createElement('style');
  styleSheet.id = 'notification-styles';
  styleSheet.textContent = notificationStyles;
  document.head.appendChild(styleSheet);
}

window.api = api;
window.mostrarErro = mostrarErro;
window.mostrarSucesso = mostrarSucesso;
window.mostrarLoading = mostrarLoading;
window.esconderLoading = esconderLoading;
window.formatarPolitico = formatarPolitico;
window.formatarPorcentagem = formatarPorcentagem;
window.formatarData = formatarData;
window.debounce = debounce;