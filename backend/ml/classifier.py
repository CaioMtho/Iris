from typing import Dict, List, Optional, Sequence, Tuple
import numpy as np
from backend.ml.embeddings import embed_texts

KEYWORDS: Dict[str, Sequence[str]] = {
    "eco": ["imposto", "privatiza", "subsídio", "estado", "tributo", "mercado"],
    "soc": ["família", "aborto", "diversidade", "ideologia", "tradição", "educação sexual"],
    "aut": ["governabilidade", "ordem", "segurança", "força", "militarização", "poder executivo"],
    "amb": ["meio ambiente", "licenciamento", "desmatamento", "amazônia", "sustentável"],
    "est": ["municipal", "federal", "autonomia", "comunidade", "ong", "governo local"]
}

ANCHOR_POS: Dict[str, str] = {
    "eco": "redução da intervenção estatal e defesa do livre mercado",
    "soc": "defesa de direitos civis e políticas progressistas",
    "aut": "defesa de instituições democráticas e separação de poderes",
    "amb": "priorizar a proteção ambiental frente a projetos degradantes",
    "est": "valorização de soluções comunitárias e locais"
}
ANCHOR_NEG: Dict[str, str] = {
    "eco": "forte papel do Estado na economia e proteção de indústrias",
    "soc": "preservação de valores e costumes tradicionais",
    "aut": "maior concentração de poder executivo para governabilidade",
    "amb": "priorizar desenvolvimento econômico sobre restrições ambientais",
    "est": "centralização estatal para coordenar políticas"
}

def make_axis_matrix(batch_size: int = 16) -> Tuple[np.ndarray, List[str]]:
    keys = list(ANCHOR_POS.keys())
    pos_texts = [ANCHOR_POS[k] for k in keys]
    neg_texts = [ANCHOR_NEG[k] for k in keys]
    pos_emb = embed_texts(pos_texts, batch_size=batch_size)
    neg_emb = embed_texts(neg_texts, batch_size=batch_size)
    axis = pos_emb - neg_emb  # (K, dim)
    norms = np.linalg.norm(axis, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    axis_normed = (axis / norms).astype(np.float32)
    return axis_normed, keys

def _keyword_choice(text: str) -> Optional[Tuple[str, float]]:
    t = (text or "").lower()
    kw_scores = {k: sum(t.count(w) for w in words) for k, words in KEYWORDS.items()}
    total = sum(kw_scores.values())
    if total == 0:
        return None
    chosen = max(kw_scores, key=lambda k: kw_scores[k])
    denom = max([1, *kw_scores.values()])
    conf = float(kw_scores[chosen]) / float(denom)
    conf = min(conf, 1.0)
    return chosen, conf

def classify_texts_batch(texts: Sequence[str],
                         axis_matrix: Optional[np.ndarray] = None,
                         axis_keys: Optional[Sequence[str]] = None,
                         batch_size: int = 32) -> List[Tuple[str, float]]:
    results: List[Optional[Tuple[str, float]]] = [None] * len(texts)
    to_embed_idx: List[int] = []
    to_embed_texts: List[str] = []

    for i, t in enumerate(texts):
        kw = _keyword_choice(t)
        if kw is not None:
            results[i] = kw
        else:
            to_embed_idx.append(i)
            to_embed_texts.append(t)

    if not to_embed_texts:
        return [r if r is not None else ("unknown", 0.0) for r in results]

    if axis_matrix is None or axis_keys is None:
        axis_matrix, axis_keys = make_axis_matrix(batch_size=batch_size)

    embs = embed_texts(to_embed_texts, batch_size=batch_size)  # (M, dim)
    if embs.ndim == 1:
        embs = embs.reshape(1, -1)

    sims = np.dot(embs, axis_matrix.T)  # (M, K)
    for row_idx, sim_row in enumerate(sims):
        best_idx = int(np.argmax(sim_row))
        best_sim = float(sim_row[best_idx])
        if sim_row.size > 1:
            second = float(np.partition(sim_row, -2)[-2])
        else:
            second = -1.0
        margin = best_sim - second
        abs_score = (best_sim + 1.0) / 2.0
        conf = float(0.6 * abs_score + 0.4 * (margin / (abs(margin) + 1e-9)))
        conf = max(0.0, min(conf, 1.0))
        eixo = axis_keys[best_idx]
        results[to_embed_idx[row_idx]] = (eixo, conf)

    return [r if r is not None else ("unknown", 0.0) for r in results]

def classify_single(text: str, axis_matrix: Optional[np.ndarray] = None,
                    axis_keys: Optional[Sequence[str]] = None, batch_size: int = 32) -> Tuple[str, float]:
    return classify_texts_batch([text], axis_matrix=axis_matrix, axis_keys=axis_keys, batch_size=batch_size)[0]
