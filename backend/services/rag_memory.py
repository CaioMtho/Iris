from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
MAX_SNIPPET_CHARS = 600

VOTOS_DEPUTADOS = {
    'Nikolas Ferreira': {
        'votos': [None, 'SIM', 'NAO', 'NAO', 'SIM', 'NAO'],
        'partido': 'PL',
        'uf': 'MG'
    },
    'Guilherme Boulos': {
        'votos': ['NAO', 'NAO', 'SIM', 'NAO', 'NAO', 'SIM'],
        'partido': 'PSOL',
        'uf': 'SP'
    },
    'Ricardo Salles': {
        'votos': ['SIM', None, 'NAO', 'NAO', None, 'NAO'],
        'partido': 'PL',
        'uf': 'SP'
    },
    'Tabata Amaral': {
        'votos': ['NAO', 'NAO', 'SIM', 'SIM', 'NAO', 'SIM'],
        'partido': 'PSB',
        'uf': 'SP'
    },
    'Celso Russomanno': {
        'votos': [None, 'SIM', 'SIM', 'SIM', 'SIM', 'SIM'],
        'partido': 'REPUBLICANOS',
        'uf': 'SP'
    }
}

VOTACOES_PROTOTIPO = [
    {
        'id': 1,
        'titulo': 'Marco Temporal das Terras Indígenas',
        'resumo': 'Projeto que estabelece que só podem ser demarcadas como terras indígenas áreas ocupadas pelos povos originários até 5 de outubro de 1988 (data da Constituição). Aprovado na Câmara, gera polêmica sobre direitos indígenas.',
        'tags': ['indigena', 'terra', 'demarcacao', 'marco temporal']
    },
    {
        'id': 2,
        'titulo': 'Lei Geral do Licenciamento Ambiental',
        'resumo': 'Nova lei que simplifica o processo de licenciamento ambiental para obras e atividades. Reduz prazos e etapas, mas ambientalistas temem flexibilização excessiva.',
        'tags': ['ambiental', 'licenciamento', 'obras', 'meio ambiente']
    },
    {
        'id': 3,
        'titulo': 'Reforma Tributária',
        'resumo': 'Substitui PIS, Cofins, ICMS, ISS e IPI por dois novos impostos: CBS (federal) e IBS (estadual/municipal). Promete simplificar sistema tributário brasileiro.',
        'tags': ['tributo', 'imposto', 'reforma', 'economia']
    },
    {
        'id': 4,
        'titulo': 'Novo Arcabouço Fiscal',
        'resumo': 'Substitui o teto de gastos públicos por novas regras que permitem crescimento real de 0,6% a 2,5% ao ano, dependendo da receita. Busca equilibrar contas públicas.',
        'tags': ['fiscal', 'gastos', 'orcamento', 'economia']
    },
    {
        'id': 5,
        'titulo': 'Imunidade Parlamentar',
        'resumo': 'Mudanças nas regras de prisão e processo criminal de deputados e senadores. Amplia proteções do mandato parlamentar.',
        'tags': ['parlamentar', 'imunidade', 'deputado', 'senador']
    },
    {
        'id': 6,
        'titulo': 'Cotas Raciais em Concursos',
        'resumo': 'Amplia cotas raciais para 20% das vagas em concursos públicos federais, incluindo área militar. Renova política de ações afirmativas.',
        'tags': ['cota', 'racial', 'concurso', 'acao afirmativa']
    }
]

def _snippet(text: str, chars: int = MAX_SNIPPET_CHARS) -> str:
    if not text:
        return ""
    s = text.replace("\n", " ").strip()
    return (s[:chars] + "...") if len(s) > chars else s

def _calculate_relevance(query: str, text: str, tags: List[str] = None) -> float:
    """Calcula relevância básica por termos encontrados"""
    query_lower = query.lower()
    text_lower = text.lower()
    score = 0
    
    # Pontuação por palavras encontradas
    query_words = query_lower.split()
    for word in query_words:
        if len(word) >= 3:
            if word in text_lower:
                score += 1
            if tags and any(word in tag for tag in tags):
                score += 0.5
    
    return score

def find_documents_for_query(q: str, limit: int = 4) -> List[Dict]:
    """Busca melhorada com relevância básica"""
    try:
        q_lower = q.lower()
        docs = []
        
        # Buscar votações
        for vot in VOTACOES_PROTOTIPO:
            relevance = _calculate_relevance(q, vot['titulo'] + " " + vot['resumo'], vot.get('tags', []))
            
            if relevance > 0:
                docs.append({
                    "id_documento_origem": f"votacao-{vot['id']}",
                    "titulo": vot['titulo'],
                    "url_fonte": None,
                    "snippet": _snippet(vot['resumo']),
                    "tipo": "votacao",
                    "relevance": relevance
                })
        
        # Buscar deputados
        for dep, info in VOTOS_DEPUTADOS.items():
            dep_text = f"{dep} {info['partido']} {info['uf']}"
            relevance = _calculate_relevance(q, dep_text)
            
            if relevance > 0:
                votos_resumo = []
                for i, voto in enumerate(info['votos'], 1):
                    if voto:
                        vot_titulo = next((v['titulo'] for v in VOTACOES_PROTOTIPO if v['id'] == i), f"Votação {i}")
                        votos_resumo.append(f"{vot_titulo}: {voto}")
                
                snippet_text = f"Deputado(a) {dep} ({info['partido']}-{info['uf']}). "
                if votos_resumo:
                    snippet_text += f"Votações: {'; '.join(votos_resumo[:2])}"
                
                docs.append({
                    "id_documento_origem": f"voto-{dep}",
                    "titulo": f"{dep} ({info['partido']}-{info['uf']})",
                    "url_fonte": None,
                    "snippet": _snippet(snippet_text),
                    "tipo": "deputado",
                    "relevance": relevance
                })
        
        # Ordenar por relevância e retornar
        docs.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return docs[:limit]
        
    except Exception as e:
        logger.error(f"Erro na busca em memória: {str(e)}")
        return []