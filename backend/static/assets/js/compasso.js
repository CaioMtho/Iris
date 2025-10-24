// Classe para gerenciar o Compasso Político
class CompassoPolitico {
  constructor() {
    this.votacoes = [];
    this.respostasUsuario = [];
    this.questaoAtual = 0;
    this.nomeUsuario = '';
    this.inicializado = false;
    
    this.initElements();
    this.bindEvents();
  }

  initElements() {
    // Elementos da DOM
    this.elements = {
      // Etapas
      etapaNome: document.getElementById('etapa-nome'),
      progressSection: document.getElementById('progress-section'),
      questoesContainer: document.getElementById('questoes-container'),
      resultadosContainer: document.getElementById('resultados-container'),
      navigationButtons: document.getElementById('navigation-buttons'),
      
      // Inputs e botões
      nomeUsuarioInput: document.getElementById('nome-usuario'),
      btnIniciar: document.getElementById('btn-iniciar'),
      btnAnterior: document.getElementById('btn-anterior'),
      btnProximo: document.getElementById('btn-proximo'),
      btnFinalizar: document.getElementById('btn-finalizar'),
      
      // Progresso
      progressBar: document.getElementById('progress-bar'),
      progressText: document.getElementById('progress-text')
    };
  }

  bindEvents() {
    // Event listeners
    this.elements.btnIniciar?.addEventListener('click', () => this.iniciarQuestionario());
    this.elements.btnAnterior?.addEventListener('click', () => { 
      this.questaoAnterior()
      window.scrollTo({ top: 0, behavior: 'smooth' })
      });
    this.elements.btnProximo?.addEventListener('click', () => { 
      this.proximaQuestao(); 
      window.scrollTo({ top: 0, behavior: 'smooth' });
  });
    this.elements.btnFinalizar?.addEventListener('click', () => this.finalizarQuestionario());
    
    // Enter no campo nome
    this.elements.nomeUsuarioInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.iniciarQuestionario();
      }
    });

    // Input no nome para habilitar botão
    this.elements.nomeUsuarioInput?.addEventListener('input', (e) => {
      const nome = e.target.value.trim();
      this.elements.btnIniciar.disabled = !nome;
    });
  }

  async iniciarQuestionario() {
    const nome = this.elements.nomeUsuarioInput.value.trim();
    
    if (!nome) {
      mostrarErro('Por favor, digite seu nome antes de continuar.');
      return;
    }

    this.nomeUsuario = nome;
    
    try {
      // Mostrar loading
      mostrarLoading(this.elements.questoesContainer);
      
      // Buscar votações da API
      const dadosPrototipo = await api.obterVotacoesPrototipo();
      this.votacoes = dadosPrototipo.votacoes || [];
      
      if (this.votacoes.length === 0) {
        throw new Error('Nenhuma votação encontrada.');
      }

      // Inicializar respostas
      this.respostasUsuario = new Array(this.votacoes.length).fill(null);
      this.questaoAtual = 0;
      
      // Mostrar interface do questionário
      this.mostrarEtapaQuestoes();
      this.renderizarQuestaoAtual();
      this.atualizarProgresso();
      
      this.inicializado = true;
      
    } catch (error) {
      console.error('Erro ao carregar votações:', error);
      mostrarErro('Erro ao carregar as questões. Tente novamente.');
    }
  }

  mostrarEtapaQuestoes() {
    // Esconder etapa do nome
    this.elements.etapaNome.style.display = 'none';
    
    // Mostrar progresso e questões
    this.elements.progressSection.style.display = 'block';
    this.elements.questoesContainer.style.display = 'block';
    this.elements.navigationButtons.style.display = 'flex';
  }

  renderizarQuestaoAtual() {
    const votacao = this.votacoes[this.questaoAtual];
    const respostaAtual = this.respostasUsuario[this.questaoAtual];
    
    const questaoHtml = `
      <div class="question" data-questao="${this.questaoAtual}">
        <div class="question-context">
          <strong>Contexto:</strong> ${votacao.contexto_atual}
        </div>
        
        <p><strong>${votacao.titulo}</strong></p>
        
        <div class="question-details">
          <p style="margin-bottom: 1rem; color: var(--neutral-700);">${votacao.resumo}</p>
          
          <p style="margin-bottom: 0.5rem;"><strong>Mudanças Propostas:</strong></p>
          <p style="margin-bottom: 1.5rem; color: var(--neutral-700);">${votacao.mudancas_propostas}</p>
          
          ${votacao.argumentos_favor && votacao.argumentos_favor.length > 0 ? `
            <div class="question-details">
              <h4>✅ Argumentos a Favor:</h4>
              <ul>
                ${votacao.argumentos_favor.map(arg => `<li>${arg}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
          
          ${votacao.argumentos_contra && votacao.argumentos_contra.length > 0 ? `
            <div class="question-details">
              <h4>❌ Argumentos Contra:</h4>
              <ul>
                ${votacao.argumentos_contra.map(arg => `<li>${arg}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
        </div>

        <div class="options">
          <label>
            <input type="radio" name="questao_${this.questaoAtual}" value="SIM" ${respostaAtual === 'SIM' ? 'checked' : ''}>
            <span>SIM - Sou a favor desta proposta</span>
          </label>
          <label>
            <input type="radio" name="questao_${this.questaoAtual}" value="NAO" ${respostaAtual === 'NAO' ? 'checked' : ''}>
            <span>NÃO - Sou contra esta proposta</span>
          </label>
          <label>
            <input type="radio" name="questao_${this.questaoAtual}" value="ABSTENCAO" ${respostaAtual === 'ABSTENCAO' ? 'checked' : ''}>
            <span>ABSTENÇÃO - Prefiro não opinar</span>
          </label>
        </div>
      </div>
    `;

    this.elements.questoesContainer.innerHTML = questaoHtml;
    
    // Adicionar event listeners para as opções
    const radios = this.elements.questoesContainer.querySelectorAll('input[type="radio"]');
    radios.forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.salvarResposta(this.questaoAtual, e.target.value);
        this.atualizarBotoes();
      });
    });
    
    this.atualizarBotoes();
  }

  salvarResposta(questaoIndex, resposta) {
    this.respostasUsuario[questaoIndex] = resposta;
  }

  questaoAnterior() {
    if (this.questaoAtual > 0) {
      this.questaoAtual--;
      this.renderizarQuestaoAtual();
      this.atualizarProgresso();
    }
  }

  proximaQuestao() {
    if (this.questaoAtual < this.votacoes.length - 1) {
      this.questaoAtual++;
      this.renderizarQuestaoAtual();
      this.atualizarProgresso();
    }
  }

  atualizarProgresso() {
    const progresso = ((this.questaoAtual + 1) / this.votacoes.length) * 100;
    this.elements.progressBar.style.setProperty('--progress-width', `${progresso}%`);
    this.elements.progressText.textContent = `Questão ${this.questaoAtual + 1} de ${this.votacoes.length}`;
  }

  atualizarBotoes() {
    // Botão anterior
    this.elements.btnAnterior.disabled = this.questaoAtual === 0;
    
    // Verificar se questão atual tem resposta
    const temResposta = this.respostasUsuario[this.questaoAtual] !== null;
    
    // Botão próximo
    const isUltimaQuestao = this.questaoAtual === this.votacoes.length - 1;
    
    if (isUltimaQuestao) {
      this.elements.btnProximo.style.display = 'none';
      this.elements.btnFinalizar.style.display = 'inline-block';
      
      // Verificar se todas as questões foram respondidas
      const todasRespondidas = this.respostasUsuario.every(r => r !== null);
      this.elements.btnFinalizar.disabled = !todasRespondidas;
    } else {
      this.elements.btnProximo.style.display = 'inline-block';
      this.elements.btnFinalizar.style.display = 'none';
      this.elements.btnProximo.disabled = !temResposta;
    }
  }

  async finalizarQuestionario() {
    try {
      // Verificar se todas as questões foram respondidas
      const todasRespondidas = this.respostasUsuario.every(r => r !== null);
      if (!todasRespondidas) {
        mostrarErro('Por favor, responda todas as questões antes de finalizar.');
        return;
      }

      // Preparar dados para envio
      const dadosQuestionario = {
        nome_usuario: this.nomeUsuario,
        votos: this.votacoes.map((votacao, index) => ({
          votacao_id: votacao.id,
          voto: this.respostasUsuario[index]
        }))
      };

      // Mostrar loading
      this.elements.questoesContainer.innerHTML = `
        <div class="loading">
          <div class="spinner"></div>
          <p>Calculando sua afinidade política...</p>
        </div>
      `;
      this.elements.navigationButtons.style.display = 'none';

      // Enviar para API
      const resultado = await api.calcularAfinidade(dadosQuestionario);
      
      // Mostrar resultados
      this.mostrarResultados(resultado);
      
    } catch (error) {
      console.error('Erro ao calcular afinidade:', error);
      mostrarErro('Erro ao calcular afinidade. Tente novamente.');
      
      // Voltar para a última questão
      this.elements.navigationButtons.style.display = 'flex';
      this.renderizarQuestaoAtual();
    }
  }

  mostrarResultados(resultado) {
    // Esconder seções do questionário
    this.elements.progressSection.style.display = 'none';
    this.elements.questoesContainer.style.display = 'none';
    this.elements.navigationButtons.style.display = 'none';
    
    // Mostrar seção de resultados
    this.elements.resultadosContainer.style.display = 'block';
    
    // Renderizar resultados
    const resultadosHtml = this.renderizarResultados(resultado);
    this.elements.resultadosContainer.innerHTML = resultadosHtml;
    
    // Scroll para o topo dos resultados
    this.elements.resultadosContainer.scrollIntoView({ 
      behavior: 'smooth', 
      block: 'start' 
    });

    mostrarSucesso('Afinidade calculada com sucesso!');
  }

  renderizarResultados(resultado) {
    const dataFormatada = new Date(resultado.data_realizacao).toLocaleString('pt-BR');
    
    return `
      <div class="resultado-compasso">
        <div class="resultado-header">
          <h2>🎯 Seus Resultados, ${resultado.nome_usuario}!</h2>
          <p class="data-realizacao">Questionário realizado em ${dataFormatada}</p>
        </div>

        <h3 style="color: var(--primary-green); margin-bottom: 1.5rem;">
          🏆 Ranking de Afinidade Política
        </h3>

        <div class="afinidade-list">
          ${resultado.ranking_afinidade.map((deputado, index) => `
            <div class="afinidade-item">
              <div class="afinidade-header">
                <div>
                  <h4>
                    ${deputado.nome}
                  </h4>
                  <p style="margin: 0; color: var(--neutral-600); font-size: 0.9rem;">
                    ${deputado.partido}${deputado.uf ? ` - ${deputado.uf}` : ''}
                  </p>
                </div>
                <div class="afinidade-percentual">
                  ${deputado.afinidade_percentual.toFixed(1)}%
                </div>
              </div>
              
              <div class="afinidade-detalhes">
                <span><strong>Votos Coincidentes:</strong> ${deputado.votos_coincidentes}</span>
                <span><strong>Votos Divergentes:</strong> ${deputado.votos_divergentes}</span>
                <span><strong>Comparáveis:</strong> ${deputado.votacoes_comparaveis}</span>
              </div>
            </div>
          `).join('')}
        </div>

        <div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 2px solid var(--neutral-gray);">
          <button class="btn btn-primary" onclick="location.reload()">
            🔄 Fazer Novo Teste
          </button>
          <button class="btn btn-secondary" onclick="window.print()" style="margin-left: 1rem;">
            🖨️ Imprimir Resultados
          </button>
        </div>
      </div>
    `;
  }

  // Método para reiniciar o questionário
  reiniciar() {
    this.votacoes = [];
    this.respostasUsuario = [];
    this.questaoAtual = 0;
    this.nomeUsuario = '';
    this.inicializado = false;

    // Resetar interface
    this.elements.etapaNome.style.display = 'block';
    this.elements.progressSection.style.display = 'none';
    this.elements.questoesContainer.style.display = 'none';
    this.elements.resultadosContainer.style.display = 'none';
    this.elements.navigationButtons.style.display = 'none';

    // Limpar campos
    this.elements.nomeUsuarioInput.value = '';
    this.elements.btnIniciar.disabled = true;

    // Focar no campo nome
    this.elements.nomeUsuarioInput.focus();
  }
}

// Inicializar quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
  // Verificar se estamos na página do compasso
  if (document.getElementById('questionario-container')) {
    window.compasso = new CompassoPolitico();
    
    // Mostrar etapa inicial
    const etapaNome = document.getElementById('etapa-nome');
    if (etapaNome) {
      etapaNome.classList.add('active');
    }
  }
});

// Funcionalidade adicional para impressão
window.addEventListener('beforeprint', () => {
  // Esconder elementos desnecessários na impressão
  const elementosParaEsconder = [
    '.navbar',
    'footer',
    '.navigation-buttons',
    'button'
  ];
  
  elementosParaEsconder.forEach(seletor => {
    const elementos = document.querySelectorAll(seletor);
    elementos.forEach(el => {
      el.style.display = 'none';
    });
  });
});

window.addEventListener('afterprint', () => {
  // Restaurar elementos após impressão
  location.reload();
});

// Função utilitária para compartilhar resultados (futura implementação)
function compartilharResultados() {
  if (navigator.share) {
    navigator.share({
      title: 'Meus Resultados do Compasso Político - Iris',
      text: 'Descobri minha afinidade política através do Iris!',
      url: window.location.href
    });
  } else {
    // Fallback para copiar URL
    navigator.clipboard.writeText(window.location.href).then(() => {
      mostrarSucesso('Link copiado para a área de transferência!');
    });
  }
}

// Exportar para uso global
window.CompassoPolitico = CompassoPolitico;
window.compartilharResultados = compartilharResultados;