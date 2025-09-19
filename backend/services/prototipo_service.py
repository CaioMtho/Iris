'''Serviço de dados para o protótipo'''
from typing import List, Dict, Any
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.schemas.prototipo import (
    QuestionarioRequest,
    ResultadoQuestionario,
    DeputadoAfinidade,
    VotacaoInfo,
    PrototipoResponse
)

from backend.services.politico_service import PoliticoService
from backend.models.models import Politico

logger = logging.getLogger(__name__)

class PrototipoService:
    """Serviço para gerenciar o protótipo IRIS"""
    
    def __init__(self):

        self.deputados_selecionados = [
            "470a3d7c-de66-432b-8496-7f192bc1036c",  # nikolas ferreira
            "a6e54a4d-31f9-4afb-9679-ea2f1e23dd88",  # guilherme boulos
            "09d41dd7-a991-41c8-9750-2998117965dc",  # ricardo salles
            "8c6a4a08-a3ef-44d2-9c5f-452374438c5f",  # tabata amaral
            "070bb287-2cb8-4f72-984d-359ea7d670b0",  # celso russomanno
            "09beda65-18c8-4120-919f-15f51a4e543b",  # kim kataguiri
            "98dd4786-666a-4f13-837e-208d94739ce6",  # amom mandel
            "816fdbd3-4830-4eae-9cd5-9b5949166037",  # erika hilton
            "80d6c6db-b15b-4ee5-95c0-94c167340da3",  # delegado palumbo
            "b2b636ed-780e-4b56-a072-b6f6e7115fba"   # hercilio diniz
        ]
        
        # Votos dos deputados nas 6 votações selecionadas
        # Chave: nome_deputado, Valor: lista de votos [vot1, vot2, vot3, vot4, vot5, vot6]
        self.votos_deputados = {
            'Nikolas Ferreira': [None, 'SIM', 'NAO', 'NAO', 'SIM', 'NAO'],
            'Guilherme Boulos': ['NAO', 'NAO', 'SIM', 'NAO', 'NAO', 'SIM'],
            'Ricardo Salles': ['SIM', None, 'NAO', 'NAO', None, 'NAO'],
            'Tabata Amaral': ['NAO', 'NAO', 'SIM', 'SIM', 'NAO', 'SIM'],
            'Celso Russomanno': [None, 'SIM', 'SIM', 'SIM', 'SIM', 'SIM'],
            'Kim Kataguiri': ['SIM', 'SIM', 'SIM', 'NAO', 'NAO', 'NAO'],
            'Amom Mandel': ['NAO', 'NAO', 'SIM', 'SIM', 'NAO', 'SIM'],
            'Erika Hilton': ['NAO', 'NAO', 'SIM', 'NAO', 'NAO', 'SIM'],
            'Delegado Palumbo': ['SIM', 'SIM', 'NAO', 'NAO', 'NAO', 'NAO'],
            'Hercílio Coelho Diniz': ['SIM', 'NAO', 'SIM', 'SIM', 'SIM', 'SIM']
        }
        
        self.votacoes_prototipo = [
            {
                'id': 1,
                'ordem': 1,
                'titulo': 'Demarcação de Terras Indígenas',
                'resumo': 'Um projeto que muda as regras para criar reservas indígenas no Brasil. A proposta diz que só podem virar terra indígena os locais onde havia índios morando no dia 5 de outubro de 1988.',
                'contexto_atual': 'Atualmente, terras tradicionalmente ocupadas por povos indígenas podem ser demarcadas mesmo que tenham sido invadidas ou que os índios tenham sido expulsos antes de 1988.',
                'mudancas_propostas': 'Só poderiam virar reservas indígenas as terras onde havia índios morando em 5 de outubro de 1988. Terras onde os índios foram expulsos antes dessa data não poderiam mais ser demarcadas. Forças de segurança e obras poderiam entrar em terras indígenas sem consultar as comunidades.',
                'argumentos_favor': [
                    'Daria mais segurança para proprietários rurais sobre suas terras',
                    'Permitiria usar essas áreas para agricultura e mineração',
                    'Seguiria uma data fixa e clara (Constituição de 1988)'
                ],
                'argumentos_contra': [
                    'Prejudicaria povos que foram expulsos de suas terras por conflitos',
                    'Violaria direitos históricos dos povos indígenas',
                    'Contrariaria tratados internacionais que o Brasil assinou',
                    'Colocaria em risco a cultura e sobrevivência indígena'
                ]
            },
            {
                'id': 2,
                'ordem': 2,
                'titulo': 'Licenciamento Ambiental',
                'resumo': 'Um projeto que muda as regras para conseguir autorização para obras e atividades que podem afetar o meio ambiente.',
                'contexto_atual': 'Para fazer obras que podem impactar a natureza, é preciso pedir autorização aos órgãos ambientais, que avaliam os riscos e podem aprovar, negar ou pedir mudanças no projeto.',
                'mudancas_propostas': 'Processos mais rápidos com prazos menores para análise. Algumas atividades ficariam dispensadas de licenciamento (como ampliação de estradas, pequenas fazendas, tratamento de água). Criação da "Licença Especial" para obras consideradas estratégicas, mesmo com alto impacto ambiental.',
                'argumentos_favor': [
                    'Reduziria burocracia e custos para empresas',
                    'Agilizaria obras importantes para o desenvolvimento',
                    'Atrairia mais investimentos para o país',
                    'Simplificaria regras confusas e contraditórias'
                ],
                'argumentos_contra': [
                    'Enfraqueceria a proteção ao meio ambiente',
                    'Aumentaria o risco de poluição e desmatamento',
                    'Reduziria controle sobre atividades perigosas',
                    'Prejudicaria comunidades que vivem próximas a grandes obras'
                ]
            },
            {
                'id': 3,
                'ordem': 3,
                'titulo': 'Reforma Tributária',
                'resumo': 'Uma mudança grande no sistema de impostos brasileiro, substituindo cinco impostos diferentes por dois impostos únicos sobre consumo.',
                'contexto_atual': 'Existem vários impostos sobre produtos e serviços (IPI, PIS, Cofins, ICMS, ISS) com regras diferentes em cada estado e município, tornando o sistema complexo.',
                'mudancas_propostas': 'Os cinco impostos atuais virariam apenas dois: um federal e outro estadual/municipal. Regras iguais para todo o Brasil. Produtos da cesta básica ficariam sem imposto. Cigarros, bebidas e outros produtos prejudiciais à saúde teriam imposto extra.',
                'argumentos_favor': [
                    'Simplificaria muito o sistema de impostos',
                    'Acabaria com a "guerra fiscal" entre estados',
                    'Tornaria os preços mais transparentes para o consumidor',
                    'Facilitaria a vida das empresas e do comércio'
                ],
                'argumentos_contra': [
                    'Poderia aumentar impostos em alguns setores',
                    'Estados e municípios perderiam autonomia para definir impostos',
                    'Pequenas empresas poderiam ser prejudicadas',
                    'Mudança muito grande pode gerar problemas na transição'
                ]
            },
            {
                'id': 4,
                'ordem': 4,
                'titulo': 'Controle de Gastos Públicos',
                'resumo': 'Novas regras para controlar quanto o governo pode gastar e se endividar, substituindo o "teto de gastos" anterior.',
                'contexto_atual': 'O governo federal precisa seguir regras para não gastar mais do que arrecada e não se endividar demais, mas as regras atuais estão sendo questionadas.',
                'mudancas_propostas': 'Criaria novos limites e controles para os gastos do governo. Estabeleceria "gatilhos" que cortariam gastos automaticamente se necessário. Permitiria alguns aumentos de gastos em situações específicas.',
                'argumentos_favor': [
                    'Garantiria responsabilidade com o dinheiro público',
                    'Controlaria a inflação e estabilizaria a economia',
                    'Daria confiança para investidores',
                    'Evitaria crise fiscal no futuro'
                ],
                'argumentos_contra': [
                    'Limitaria investimentos em áreas importantes como saúde e educação',
                    'Poderia dificultar respostas a crises econômicas',
                    'Restringiria programas sociais',
                    'Priorizaria interesses financeiros sobre necessidades da população'
                ]
            },
            {
                'id': 5,
                'ordem': 5,
                'titulo': 'Proteção de Deputados e Senadores',
                'resumo': 'Mudanças nas regras para prender deputados e senadores ou abrir processos criminais contra eles.',
                'contexto_atual': 'Deputados e senadores têm algumas proteções especiais (imunidades), mas podem ser presos e processados em certas situações, especialmente por crimes graves.',
                'mudancas_propostas': 'Seria mais difícil prender deputados e senadores. O Congresso teria mais poder para autorizar ou não investigações. Aumentaria as proteções contra processos judiciais.',
                'argumentos_favor': [
                    'Protegeria parlamentares de perseguições políticas',
                    'Garantiria independência do Congresso',
                    'Evitaria uso político da Justiça contra opositores',
                    'Preservaria a separação entre os poderes'
                ],
                'argumentos_contra': [
                    'Dificultaria combate à corrupção',
                    'Criaria privilégios excessivos para políticos',
                    'Enfraqueceria a Justiça e investigações',
                    'Geraria impunidade para crimes graves'
                ]
            },
            {
                'id': 6,
                'ordem': 6,
                'titulo': 'Cotas Raciais em Concursos Públicos',
                'resumo': 'Ampliação das cotas raciais para concursos públicos federais, aumentando a porcentagem de vagas reservadas.',
                'contexto_atual': 'Desde 2014, 20% das vagas em concursos federais são reservadas para pessoas negras (pretas e pardas).',
                'mudancas_propostas': 'Aumentaria de 20% para 30% as vagas reservadas. Incluiria também indígenas e quilombolas nas cotas. Valeria para qualquer concurso com 2 ou mais vagas. Sistema de autodeclaração racial.',
                'argumentos_favor': [
                    'Corrigiria desigualdades históricas no serviço público',
                    'Aumentaria representatividade de grupos marginalizados',
                    'Democratizaria acesso a cargos públicos',
                    'Promoveria justiça social e reparação histórica'
                ],
                'argumentos_contra': [
                    'Poderia prejudicar candidatos por critérios raciais',
                    'Questionamentos sobre autodeclaração e fraudes',
                    'Mérito individual deveria ser o único critério',
                    'Geraria divisões e conflitos raciais'
                ]
            }
        ]
    
    def get_votacoes_prototipo(self) -> PrototipoResponse:
        """Retorna informações das votações para o frontend"""
        votacoes_info = [
            VotacaoInfo(**votacao) for votacao in self.votacoes_prototipo
        ]
        
        return PrototipoResponse(
            votacoes=votacoes_info,
            total_votacoes=len(votacoes_info)
        )
    
    def calcular_afinidade(self, db: Session, request: QuestionarioRequest) -> ResultadoQuestionario:
        """Calcula afinidade do usuário com os deputados"""
        
        try:
            politicos = PoliticoService.listar_politicos(db)
            
            deputados_relevantes = [
                p for p in politicos 
                if p.nome in self.votos_deputados
            ]
            
            if not deputados_relevantes:
                raise HTTPException(404, "Nenhum deputado selecionado encontrado no banco")
            
            votos_usuario = {voto.votacao_id - 1: voto.voto for voto in request.votos}
            
            resultados_deputados = []
            
            for deputado in deputados_relevantes:
                if deputado.nome in self.votos_deputados:
                    afinidade = self._calcular_afinidade_deputado(
                        votos_usuario, 
                        self.votos_deputados[deputado.nome],
                        deputado
                    )
                    resultados_deputados.append(afinidade)
            
            # Ordenar por afinidade (maior primeiro)
            resultados_deputados.sort(key=lambda x: x.afinidade_percentual, reverse=True)
            
            resumo_estatistico = self._calcular_resumo_estatistico(resultados_deputados)
            
            return ResultadoQuestionario(
                nome_usuario=request.nome_usuario,
                data_realizacao=datetime.now(),
                ranking_afinidade=resultados_deputados,
                resumo_estatistico=resumo_estatistico
            )
            
        except Exception as e:
            logger.error("Erro ao calcular afinidade: %s", str(e))
            raise HTTPException(500, f"Erro interno ao calcular afinidade: {str(e)}") from e
    
    def _calcular_afinidade_deputado(self, votos_usuario: Dict, votos_deputado: List, deputado) -> DeputadoAfinidade:
        """Calcula afinidade específica com um deputado usando a fórmula de Jaccard modificada"""
        
        coincidentes = 0
        divergentes = 0
        comparaveis = 0
        detalhes = {}
        
        for index, value in enumerate(votos_deputado):
            if index not in votos_usuario:
                continue
                
            voto_user = value
            voto_dep = value
            
            if voto_user == 'ABSTENCAO' or voto_dep is None:
                detalhes[f'votacao_{index + 1}'] = {
                    'usuario': voto_user,
                    'deputado': voto_dep or 'AUSENTE',
                    'resultado': 'NAO_COMPARAVEL'
                }
                continue
            
            comparaveis += 1
            
            if voto_user == voto_dep:
                coincidentes += 1
                detalhes[f'votacao_{index+1}'] = {
                    'usuario': voto_user,
                    'deputado': voto_dep,
                    'resultado': 'COINCIDENTE'
                }
            else:
                divergentes += 1
                detalhes[f'votacao_{index}'] = {
                    'usuario': voto_user,
                    'deputado': voto_dep,
                    'resultado': 'DIVERGENTE'
                }
        
        if comparaveis == 0:
            afinidade_percentual = 0.0
        else:
            afinidade_percentual = ((coincidentes - divergentes) / comparaveis) * 100
        
        return DeputadoAfinidade(
            id=deputado.id,
            nome=deputado.nome,
            partido=deputado.partido,
            uf=deputado.uf,
            afinidade_percentual=round(afinidade_percentual, 2),
            votos_coincidentes=coincidentes,
            votos_divergentes=divergentes,
            votacoes_comparaveis=comparaveis,
            detalhes=detalhes
        )
    
    def _calcular_resumo_estatistico(self, resultados: List[DeputadoAfinidade]) -> Dict[str, Any]:
        """Calcula estatísticas gerais do questionário"""
        
        if not resultados:
            return {
                'maior_afinidade': 0,
                'menor_afinidade': 0,
                'afinidade_media': 0,
                'total_deputados_comparados': 0,
                'deputado_mais_proximo': None,
                'deputado_mais_distante': None
            }
        
        afinidades = [r.afinidade_percentual for r in resultados]
        
        return {
            'maior_afinidade': max(afinidades),
            'menor_afinidade': min(afinidades),
            'afinidade_media': round(sum(afinidades) / len(afinidades), 2),
            'total_deputados_comparados': len(resultados),
            'deputado_mais_proximo': resultados[0].nome,
            'deputado_mais_distante': resultados[-1].nome,
            'spread_afinidade': round(max(afinidades) - min(afinidades), 2)
        }