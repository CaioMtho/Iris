// Arquivo principal de JavaScript
document.addEventListener('DOMContentLoaded', function() {
  initializeApp();
});

// Inicializar aplicação
function initializeApp() {
  setupMobileMenu();
  setupModals();
  setupNotifications();
  
  // Marcar página ativa no menu
  markActiveNavItem();
  
  // Inicializar funcionalidades específicas da página
  const currentPage = getCurrentPage();
  switch(currentPage) {
    case 'index':
      initializeHomePage();
      break;
    case 'politicos':
      initializePoliticosPage();
      break;
    case 'compasso':
      initializeCompassoPage();
      break;
    case 'politico-detail':
      initializePoliticoDetailPage();
      break;
    case 'documentacao':
      initializeDocumentacaoPage();
      break;
  }
}

// Obter página atual baseada na URL
function getCurrentPage() {
  const path = window.location.pathname;
  const filename = path.split('/').pop().split('.')[0];
  return filename || 'index';
}

// Marcar item ativo no menu de navegação
function markActiveNavItem() {
  const currentPage = getCurrentPage();
  const navLinks = document.querySelectorAll('.navbar a');
  
  navLinks.forEach(link => {
    link.classList.remove('active');
    const href = link.getAttribute('href');
    if (href) {
      const linkPage = href.split('/').pop().split('.')[0];
      if (linkPage === currentPage || (currentPage === 'index' && href.includes('index'))) {
        link.classList.add('active');
      }
    }
  });
}

// Configurar menu mobile
function setupMobileMenu() {
  const mobileToggle = document.querySelector('.mobile-menu-toggle');
  const navMenu = document.querySelector('.navbar ul');
  
  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener('click', () => {
      navMenu.classList.toggle('show');
    });
    
    // Fechar menu ao clicar em um link
    navMenu.addEventListener('click', (e) => {
      if (e.target.tagName === 'A') {
        navMenu.classList.remove('show');
      }
    });
    
    // Fechar menu ao redimensionar para desktop
    window.addEventListener('resize', () => {
      if (window.innerWidth > 768) {
        navMenu.classList.remove('show');
      }
    });
  }
}

// Configurar modais
function setupModals() {
  // Fechar modal ao clicar no X ou fora do modal
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-close') || e.target.classList.contains('modal')) {
      closeModal();
    }
  });
  
  // Fechar modal com ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal();
    }
  });
}

// Abrir modal
function openModal(content) {
  let modal = document.querySelector('.modal');
  
  if (!modal) {
    modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-content">
        <button class="modal-close">&times;</button>
        <div class="modal-body"></div>
      </div>
    `;
    document.body.appendChild(modal);
  }
  
  const modalBody = modal.querySelector('.modal-body');
  modalBody.innerHTML = content;
  modal.style.display = 'block';
  
  // Prevenir scroll do body
  document.body.style.overflow = 'hidden';
}

// Fechar modal
function closeModal() {
  const modal = document.querySelector('.modal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }
}

// Configurar sistema de notificações
function setupNotifications() {
  // Criar container de notificações se não existir
  if (!document.querySelector('.notifications-container')) {
    const container = document.createElement('div');
    container.className = 'notifications-container';
    document.body.appendChild(container);
  }
}

// ========== FUNCIONALIDADES DA PÁGINA INICIAL ==========
async function initializeHomePage() {
  await loadHomeStats();
  setupHomeAnimations();
}

async function loadHomeStats() {
  const statsElements = {
    politicos: document.querySelector('[data-stat="politicos"]'),
    partidos: document.querySelector('[data-stat="partidos"]'),
    estados: document.querySelector('[data-stat="estados"]'),
    votacoes: document.querySelector('[data-stat="votacoes"]')
  };
  
  try {
    const stats = await api.obterEstatisticas();
    
    if (statsElements.politicos) {
      animateNumber(statsElements.politicos, stats.totalPoliticos);
    }
    if (statsElements.partidos) {
      animateNumber(statsElements.partidos, stats.totalPartidos);
    }
    if (statsElements.estados) {
      animateNumber(statsElements.estados, stats.totalEstados);
    }
    if (statsElements.votacoes) {
      animateNumber(statsElements.votacoes, stats.totalVotacoes);
    }
  } catch (error) {
    console.error('Erro ao carregar estatísticas:', error);
  }
}

function setupHomeAnimations() {
  // Adicionar animações aos elementos quando entram na viewport
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('fade-in-up');
      }
    });
  }, observerOptions);
  
  // Observar elementos que devem ser animados
  document.querySelectorAll('.stat-card, .card').forEach(el => {
    observer.observe(el);
  });
}

// Animar números (contador)
function animateNumber(element, targetNumber, duration = 2000) {
  const startNumber = 0;
  const increment = targetNumber / (duration / 16); // 60 FPS
  let currentNumber = startNumber;
  
  const timer = setInterval(() => {
    currentNumber += increment;
    if (currentNumber >= targetNumber) {
      currentNumber = targetNumber;
      clearInterval(timer);
    }
    element.textContent = Math.floor(currentNumber).toLocaleString('pt-BR');
  }, 16);
}

// ========== FUNCIONALIDADES DA PÁGINA DE POLÍTICOS ==========
async function initializePoliticosPage() {
  await loadPoliticos();
  setupPoliticosSearch();
  setupPoliticosFilters();
}

async function loadPoliticos(filtros = {}) {
  const container = document.querySelector('#politicos-container');
  if (!container) return;
  
  mostrarLoading(container);
  
  try {
    const politicos = await api.buscarPoliticosComFiltros(filtros);
    renderPoliticos(politicos);
  } catch (error) {
    mostrarErro('Erro ao carregar políticos. Tente novamente.');
    container.innerHTML = '<p class="text-center">Erro ao carregar dados.</p>';
  }
}

function renderPoliticos(politicos) {
  const container = document.querySelector('#politicos-container');
  if (!container) return;
  
  if (politicos.length === 0) {
    container.innerHTML = '<p class="text-center">Nenhum político encontrado.</p>';
    return;
  }
  
  const html = politicos.map(politico => {
    const p = formatarPolitico(politico);
    return `
      <div class="card" data-politico-id="${politico.id}">
        <div class="card-header">
          <h3 class="card-title">${p.nomeFormatado}</h3>
          <p class="card-subtitle">${p.partidoFormatado} - ${p.estadoFormatado}</p>
        </div>
        <div class="card-body">
          <p class="card-text">${p.cargoFormatado}</p>
        </div>
      </div>
    `;
  }).join('');
  
  container.innerHTML = html;
  
  // Adicionar event listeners aos cards
  container.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => {
      const politicoId = card.dataset.politicoId;
      showPoliticoModal(politicoId);
    });
  });
}

function setupPoliticosSearch() {
  const searchInput = document.querySelector('#search-politicos');
  if (!searchInput) return;
  
  const debouncedSearch = debounce(async (termo) => {
    const filtros = { nome: termo };
    await loadPoliticos(filtros);
  }, 300);
  
  searchInput.addEventListener('input', (e) => {
    debouncedSearch(e.target.value);
  });
}

async function setupPoliticosFilters() {
  const partidoSelect = document.querySelector('#filter-partido');
  const estadoSelect = document.querySelector('#filter-estado');
  
  if (partidoSelect) {
    try {
      const partidos = await api.obterPartidos();
      partidoSelect.innerHTML = '<option value="">Todos os partidos</option>' +
        partidos.map(partido => `<option value="${partido}">${partido}</option>`).join('');
    } catch (error) {
      console.error('Erro ao carregar partidos:', error);
    }
  }
  
  if (estadoSelect) {
    try {
      const estados = await api.obterEstados();
      estadoSelect.innerHTML = '<option value="">Todos os estados</option>' +
        estados.map(estado => `<option value="${estado}">${estado}</option>`).join('');
    } catch (error) {
      console.error('Erro ao carregar estados:', error);
    }
  }
  
  // Event listeners para filtros
  [partidoSelect, estadoSelect].forEach(select => {
    if (select) {
      select.addEventListener('change', applyFilters);
    }
  });
}

function applyFilters() {
  const searchTerm = document.querySelector('#search-politicos')?.value || '';
  const partido = document.querySelector('#filter-partido')?.value || '';
  const estado = document.querySelector('#filter-estado')?.value || '';
  
  const filtros = {};
  if (searchTerm) filtros.nome = searchTerm;
  if (partido) filtros.partido = partido;
  if (estado) filtros.estado = estado;
  
  loadPoliticos(filtros);
}

async function showPoliticoModal(politicoId) {
  try {
    const politico = await api.buscarPolitico(politicoId);
    const p = formatarPolitico(politico);
    
    const content = `
      <h2>${p.nomeFormatado}</h2>
      <div class="politico-details">
        <p><strong>Partido:</strong> ${p.partidoFormatado}</p>
        <p><strong>Estado:</strong> ${p.estadoFormatado}</p>
        <p><strong>Cargo:</strong> ${p.cargoFormatado}</p>
      </div>
      <div class="modal-actions">
        <a href="pages/politico-detail.html?id=${politicoId}" class="btn">Ver Detalhes Completos</a>
      </div>
    `;
    
    openModal(content);
  } catch (error) {
    mostrarErro('Erro ao carregar detalhes do político.');
  }
}

// ========== FUNCIONALIDADES DO COMPASSO POLÍTICO ==========
async function initializeCompassoPage() {
  await loadVotacoesPrototipo();
  setupCompassoForm();
}

async function loadVotacoesPrototipo() {
  const container = document.querySelector('#votacoes-container');
  if (!container) return;
  
  try {
    const data = await api.obterVotacoesPrototipo();
    renderVotacoes(data.votacoes || []);
  } catch (error) {
    mostrarErro('Erro ao carregar votações.');
    container.innerHTML = '<p class="text-center">Erro ao carregar votações.</p>';
  }
}

function renderVotacoes(votacoes) {
  const container = document.querySelector('#votacoes-container');
  if (!container) return;
  
  const html = votacoes.map((votacao, index) => `
    <div class="question">
      <p>${index + 1}. ${votacao.descricao}</p>
      <div class="options">
        <label>
          <input type="radio" name="votacao_${votacao.id}" value="SIM" required>
          Sim
        </label>
        <label>
          <input type="radio" name="votacao_${votacao.id}" value="NAO" required>
          Não
        </label>
        <label>
          <input type="radio" name="votacao_${votacao.id}" value="ABSTENCÃO" required>
          Abstenção
        </label>
      </div>
    </div>
  `).join('');
  
  container.innerHTML = html;
}

function setupCompassoForm() {
  const form = document.querySelector('#compasso-form');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const nomeUsuario = document.querySelector('#nome-usuario')?.value;
    if (!nomeUsuario) {
      mostrarErro('Por favor, informe seu nome.');
      return;
    }
    
    const formData = new FormData(form);
    const votos = [];
    
    // Coletar votos do formulário
    for (const [key, value] of formData.entries()) {
      if (key.startsWith('votacao_')) {
        const votacaoId = parseInt(key.replace('votacao_', ''));
        votos.push({
          votacao_id: votacaoId,
          voto: value
        });
      }
    }
    
    if (votos.length === 0) {
      mostrarErro('Por favor, responda todas as questões.');
      return;
    }
    
    try {
      const resultado = await api.calcularAfinidade({
        nome_usuario: nomeUsuario,
        votos: votos
      });
      
      showResultadoCompasso(resultado);
    } catch (error) {
      mostrarErro('Erro ao calcular afinidade. Tente novamente.');
    }
  });
}

function showResultadoCompasso(resultado) {
  const content = `
    <h2>Seu Resultado</h2>
    <div class="resultado-compasso">
      <h3>Políticos com maior afinidade:</h3>
      <div class="afinidade-list">
        ${resultado.politicos_afinidade.map(item => `
          <div class="afinidade-item">
            <h4>${item.nome}</h4>
            <p>Afinidade: ${(item.afinidade * 100).toFixed(1)}%</p>
            <p>${item.partido} - ${item.estado}</p>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  
  openModal(content);
}

// ========== FUNCIONALIDADES DA PÁGINA DE DETALHES ==========
async function initializePoliticoDetailPage() {
  const urlParams = new URLSearchParams(window.location.search);
  const politicoId = urlParams.get('id');
  
  if (politicoId) {
    await loadPoliticoDetails(politicoId);
  } else {
    mostrarErro('ID do político não encontrado.');
  }
}

async function loadPoliticoDetails(politicoId) {
  const container = document.querySelector('#politico-detail-container');
  if (!container) return;
  
  mostrarLoading(container);
  
  try {
    const politico = await api.buscarPolitico(politicoId);
    renderPoliticoDetails(politico);
  } catch (error) {
    mostrarErro('Erro ao carregar detalhes do político.');
    container.innerHTML = '<p class="text-center">Erro ao carregar dados.</p>';
  }
}

function renderPoliticoDetails(politico) {
  const container = document.querySelector('#politico-detail-container');
  if (!container) return;
  
  const p = formatarPolitico(politico);
  
  container.innerHTML = `
    <div class="politico-header">
      <h1>${p.nomeFormatado}</h1>
      <div class="politico-info">
        <span class="info-item">${p.partidoFormatado}</span>
        <span class="info-item">${p.estadoFormatado}</span>
        <span class="info-item">${p.cargoFormatado}</span>
      </div>
    </div>
    
    <div class="politico-content">
      <div class="info-section">
        <h2>Informações Gerais</h2>
        <p>Detalhes completos sobre ${p.nomeFormatado} serão exibidos aqui quando disponíveis.</p>
      </div>
    </div>
  `;
}

// ========== FUNCIONALIDADES DA PÁGINA DE DOCUMENTAÇÃO ==========
function initializeDocumentacaoPage() {
  // Implementar funcionalidades específicas da documentação
  console.log('Página de documentação inicializada');
}

// Exportar funções para uso global
window.openModal = openModal;
window.closeModal = closeModal;
window.showPoliticoModal = showPoliticoModal;

