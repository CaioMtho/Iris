// Configuração da API
const API_BASE_URL = 'http://localhost:8000/api/v1';

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
      
      // Se não há conteúdo (204), retorna null
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

  // Listar todos os políticos
  async listarPoliticos() {
    return this.makeRequest('/politicos/');
  }

  // Buscar político por ID
  async buscarPolitico(id) {
    return this.makeRequest(`/politicos/${id}`);
  }

  // Criar novo político
  async criarPolitico(dadosPolitico) {
    return this.makeRequest('/politicos/', {
      method: 'POST',
      body: JSON.stringify(dadosPolitico)
    });
  }

  // Atualizar político
  async atualizarPolitico(id, dadosPolitico) {
    return this.makeRequest(`/politicos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(dadosPolitico)
    });
  }

  // Criar ou atualizar político (upsert)
  async upsertPolitico(id, dadosPolitico) {
    return this.makeRequest(`/politicos/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(dadosPolitico)
    });
  }

  // Deletar político
  async deletarPolitico(id) {
    return this.makeRequest(`/politicos/${id}`, {
      method: 'DELETE'
    });
  }

  // Listar políticos por partido
  async listarPoliticosPorPartido(partido) {
    return this.makeRequest(`/politicos/partido/${encodeURIComponent(partido)}`);
  }

  // ========== ENDPOINTS DE PROTÓTIPO ==========

  // Obter votações do protótipo
  async obterVotacoesPrototipo() {
    return this.makeRequest('/prototipo/');
  }

  // Calcular afinidade política
  async calcularAfinidade(dadosQuestionario) {
    return this.makeRequest('/prototipo/calcular-afinidade', {
      method: 'POST',
      body: JSON.stringify(dadosQuestionario)
    });
  }

  // ========== MÉTODOS UTILITÁRIOS ==========

  // Buscar políticos com filtros
  async buscarPoliticosComFiltros(filtros = {}) {
    let politicos = await this.listarPoliticos();
    
    // Aplicar filtros localmente
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
        p.estado === filtros.estado
      );
    }
    
    return politicos;
  }

  // Obter lista única de partidos
  async obterPartidos() {
    const politicos = await this.listarPoliticos();
    const partidos = [...new Set(politicos.map(p => p.partido))];
    return partidos.sort();
  }

  // Obter lista única de estados
  async obterEstados() {
    const politicos = await this.listarPoliticos();
    const estados = [...new Set(politicos.map(p => p.estado))];
    return estados.sort();
  }

  // Obter estatísticas gerais
  async obterEstatisticas() {
    try {
      const [politicos, votacoes] = await Promise.all([
        this.listarPoliticos(),
        this.obterVotacoesPrototipo()
      ]);

      const partidos = new Set(politicos.map(p => p.partido));
      const estados = new Set(politicos.map(p => p.estado));

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
}

// Instância global da API
const api = new ApiService();

// Funções utilitárias para tratamento de erros
function mostrarErro(mensagem) {
  console.error(mensagem);
  
  // Criar notificação de erro
  const notification = document.createElement('div');
  notification.className = 'notification error';
  notification.innerHTML = `
    <div class="notification-content">
      <span class="notification-icon">⚠️</span>
      <span class="notification-message">${mensagem}</span>
      <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
  `;
  
  // Adicionar ao body se não existir container de notificações
  let container = document.querySelector('.notifications-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notifications-container';
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
  
  // Criar notificação de sucesso
  const notification = document.createElement('div');
  notification.className = 'notification success';
  notification.innerHTML = `
    <div class="notification-content">
      <span class="notification-icon">✅</span>
      <span class="notification-message">${mensagem}</span>
      <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
  `;
  
  // Adicionar ao body se não existir container de notificações
  let container = document.querySelector('.notifications-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notifications-container';
    document.body.appendChild(container);
  }
  
  container.appendChild(notification);
  
  // Remover automaticamente após 3 segundos
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

// Função para formatar dados do político para exibição
function formatarPolitico(politico) {
  return {
    ...politico,
    nomeFormatado: politico.nome || 'Nome não informado',
    partidoFormatado: politico.partido || 'Partido não informado',
    estadoFormatado: politico.estado || 'Estado não informado',
    cargoFormatado: politico.cargo || 'Cargo não informado'
  };
}

// Função para debounce (evitar muitas requisições durante digitação)
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

// Exportar para uso global
window.api = api;
window.mostrarErro = mostrarErro;
window.mostrarSucesso = mostrarSucesso;
window.mostrarLoading = mostrarLoading;
window.esconderLoading = esconderLoading;
window.formatarPolitico = formatarPolitico;
window.debounce = debounce;

