import zipfile
import io
import csv
import json
import logging
from typing import Dict, List, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from backend.db.database import SessionLocal
from backend.ml.embeddings import embed_texts
from backend.ml.classifier import make_axis_matrix, classify_texts_batch

logger = logging.getLogger(__name__)

VOTO_MAP = {"sim": 1.0, "nao": -1.0, "abstencao": 0.0, "ausente": 0.0}

EXPECTED = {
    "politicos": "politicos.json",
    "documentos": "documentos.json",
    "votacoes": "votacoes.csv",
    "votos": "votos.csv",
    "discursos": "discursos.json"
}

def ensure_votacoes_eixo_table(session) -> None:
    session.execute(text("""
    CREATE TABLE IF NOT EXISTS votacoes_eixo (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      votacao_id UUID REFERENCES votacoes(id) ON DELETE CASCADE,
      eixo TEXT NOT NULL,
      eixo_conf REAL,
      metodo TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """))
    session.commit()

def find_politico_by_id_camara(session, id_camara: int) -> Optional[str]:
    row = session.execute(text("SELECT id FROM politicos WHERE id_camara = :id LIMIT 1"), {"id": int(id_camara)}).fetchone()
    return row[0] if row else None

def ingest_politicos(session, politicos_list: List[Dict]) -> List[str]:
    inserted_ids: List[str] = []
    for p in politicos_list:
        id_camara = p.get("id_camara")
        nome = p.get("nome")
        partido = p.get("partido")
        cargo = p.get("cargo")
        votos_2022 = p.get("votos_2022")
        ativo = p.get("ativo", True)

        if id_camara is not None:
            existing = session.execute(text("SELECT id FROM politicos WHERE id_camara = :id"), {"id": int(id_camara)}).fetchone()
            if existing:
                session.execute(
                    text("UPDATE politicos SET nome=:nome, partido=:partido, cargo=:cargo, votos_2022=:votos_2022, ativo=:ativo, updated_at=NOW() WHERE id = :id"),
                    {"nome": nome, "partido": partido, "cargo": cargo, "votos_2022": votos_2022, "ativo": ativo, "id": existing[0]}
                )
                inserted_ids.append(existing[0])
                continue

        existing_name = session.execute(text("SELECT id FROM politicos WHERE lower(nome)=:nome LIMIT 1"), {"nome": str(nome).lower()}).fetchone()
        if existing_name:
            inserted_ids.append(existing_name[0])
            session.execute(
                text("UPDATE politicos SET partido=:partido, cargo=:cargo, updated_at=NOW() WHERE id=:id"),
                {"partido": partido, "cargo": cargo, "id": existing_name[0]}
            )
            continue

        res = session.execute(
            text("""
            INSERT INTO politicos (id_camara, nome, partido, cargo, votos_2022, ativo, historico_ici, created_at, updated_at)
            VALUES (:id_camara, :nome, :partido, :cargo, :votos_2022, :ativo, '{}'::jsonb, NOW(), NOW())
            RETURNING id
            """),
            {"id_camara": id_camara, "nome": nome, "partido": partido, "cargo": cargo, "votos_2022": votos_2022, "ativo": ativo}
        )
        new_id = res.fetchone()[0]
        inserted_ids.append(new_id)
    session.commit()
    return inserted_ids

def ingest_documentos(session, documentos_list: List[Dict]) -> List[Dict]:
    created = []
    for d in documentos_list:
        id_doc = d.get("id_documento_origem")
        politico_id_camara = d.get("politico_id_camara")
        titulo = d.get("titulo")
        tipo = d.get("tipo", "discurso")
        data_pub = d.get("data_publicacao")
        url = d.get("url_fonte")
        conteudo = d.get("conteudo_original", "")
        ementa = d.get("ementa") or d.get("resumo_simplificado")

        politico_interno = None
        if politico_id_camara is not None:
            politico_interno = find_politico_by_id_camara(session, int(politico_id_camara))

        res = session.execute(
            text("""
            INSERT INTO documentos_politicos (id_documento_origem, politico_id, titulo, tipo, data_publicacao, url_fonte, ementa, conteudo_original, resumo_simplificado, created_at, updated_at)
            VALUES (:id_documento_origem, :politico_id, :titulo, :tipo, :data_publicacao, :url_fonte, :ementa, :conteudo_original, :resumo_simplificado, NOW(), NOW())
            RETURNING id
            """),
            {
                "id_documento_origem": id_doc,
                "politico_id": politico_interno,
                "titulo": titulo,
                "tipo": tipo,
                "data_publicacao": data_pub,
                "url_fonte": url,
                "ementa": ementa,
                "conteudo_original": conteudo,
                "resumo_simplificado": d.get("resumo_simplificado")
            }
        )
        new_id = res.fetchone()[0]
        created.append({"id": new_id, "orig": id_doc})
    session.commit()
    return created

def ingest_votacoes_csv(session, csv_bytes: bytes) -> Dict[str, str]:
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
    mapping: Dict[str, str] = {}
    for row in reader:
        id_vot_origem = row.get("id_votacao_origem")
        documento_origem = row.get("documento_id_origem")
        data_vot = row.get("data_votacao")
        resultado = row.get("resultado")
        descricao = row.get("descricao")
        doc_id = None
        if documento_origem:
            r = session.execute(text("SELECT id FROM documentos_politicos WHERE id_documento_origem = :o LIMIT 1"), {"o": documento_origem}).fetchone()
            doc_id = r[0] if r else None

        res = session.execute(
            text("""
            INSERT INTO votacoes (id_votacao_origem, documento_id, data_votacao, resultado, descricao, created_at, updated_at)
            VALUES (:id_votacao_origem, :documento_id, :data_votacao, :resultado, :descricao, NOW(), NOW())
            RETURNING id
            """),
            {"id_votacao_origem": id_vot_origem, "documento_id": doc_id, "data_votacao": data_vot, "resultado": resultado, "descricao": descricao}
        )
        new_id = res.fetchone()[0]
        mapping[str(id_vot_origem)] = new_id
    session.commit()
    return mapping

def ingest_votos_csv(session, csv_bytes: bytes, votacao_map: Dict[str, str]) -> int:
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
    count = 0
    for row in reader:
        id_vot_origem = str(row.get("id_votacao_origem"))
        politico_id_camara = row.get("politico_id_camara")
        voto = (row.get("voto") or "").strip().lower()
        votacao_id = votacao_map.get(id_vot_origem)
        if not votacao_id:
            continue
        politico_interno = None
        if politico_id_camara:
            try:
                politico_interno = find_politico_by_id_camara(session, int(politico_id_camara))
            except Exception:
                politico_interno = None
        if not politico_interno:
            continue
        session.execute(
            text("INSERT INTO votos_politicos (votacao_id, politico_id, voto, created_at, updated_at) VALUES (:votacao_id, :politico_id, :voto, NOW(), NOW())"),
            {"votacao_id": votacao_id, "politico_id": politico_interno, "voto": voto}
        )
        count += 1
    session.commit()
    return count

def compute_document_embeddings(session, batch_size: int = 32) -> int:
    rows = session.execute(text("SELECT id, COALESCE(ementa, LEFT(conteudo_original, 2000)) as text FROM documentos_politicos WHERE embedding_documento IS NULL")).fetchall()
    if not rows:
        return 0
    ids = [r[0] for r in rows]
    texts = [r[1] or "" for r in rows]
    total = 0
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        embs = embed_texts(batch_texts, batch_size=batch_size)
        for _id, emb in zip(batch_ids, embs):
            emb_list = [float(x) for x in emb.tolist()]
            session.execute(text("UPDATE documentos_politicos SET embedding_documento = :emb, updated_at = NOW() WHERE id = :id"), {"emb": emb_list, "id": _id})
            total += 1
        session.commit()
    return total

def classify_votacoes(session, batch_size: int = 32) -> int:
    ensure_votacoes_eixo_table(session)
    # get axis matrix once
    axis_matrix, axis_keys = make_axis_matrix(batch_size=batch_size)
    rows = session.execute(text("SELECT v.id, COALESCE(v.descricao, d.ementa, LEFT(d.conteudo_original,2000)) as text FROM votacoes v LEFT JOIN documentos_politicos d ON v.documento_id = d.id")).fetchall()
    if not rows:
        return 0
    votacao_ids = [r[0] for r in rows]
    texts = [r[1] or "" for r in rows]
    results = classify_texts_batch(texts, axis_matrix=axis_matrix, axis_keys=axis_keys, batch_size=batch_size)
    inserted = 0
    for vid, (eixo, conf) in zip(votacao_ids, results):
        exists = session.execute(text("SELECT id FROM votacoes_eixo WHERE votacao_id = :vid LIMIT 1"), {"vid": vid}).fetchone()
        method = "hybrid"
        if exists:
            session.execute(text("UPDATE votacoes_eixo SET eixo = :e, eixo_conf = :c, metodo = :m WHERE id = :id"), {"e": eixo, "c": conf, "m": method, "id": exists[0]})
        else:
            session.execute(text("INSERT INTO votacoes_eixo (votacao_id, eixo, eixo_conf, metodo, created_at) VALUES (:vid, :e, :c, :m, NOW())"), {"vid": vid, "e": eixo, "c": conf, "m": method})
            inserted += 1
    session.commit()
    return inserted

def compute_scores(session, batch_size: int = 32) -> int:
    axes = ["eco", "soc", "aut", "amb", "est"]
    politicos = session.execute(text("SELECT id FROM politicos")).fetchall()
    updated = 0
    for p in politicos:
        pid = p[0]
        rows = session.execute(text("""
            SELECT vp.voto, ve.eixo FROM votos_politicos vp
            JOIN votacoes_eixo ve ON vp.votacao_id = ve.votacao_id
            WHERE vp.politico_id = :pid
        """), {"pid": pid}).fetchall()
        if not rows:
            continue
        vals = {a: [] for a in axes}
        for voto_raw, eixo in rows:
            v = VOTO_MAP.get((voto_raw or "").lower(), 0.0)
            if eixo in vals:
                vals[eixo].append(v)
        final = {a: (float(sum(vals[a]) / len(vals[a])) if vals[a] else None) for a in axes}
        summary = "eco:{eco:.3f} soc:{soc:.3f} aut:{aut:.3f} amb:{amb:.3f} est:{est:.3f}".format(
            eco=(final["eco"] if final["eco"] is not None else 0.0),
            soc=(final["soc"] if final["soc"] is not None else 0.0),
            aut=(final["aut"] if final["aut"] is not None else 0.0),
            amb=(final["amb"] if final["amb"] is not None else 0.0),
            est=(final["est"] if final["est"] is not None else 0.0)
        )
        emb = embed_texts([summary], batch_size=batch_size)[0].tolist()
        session.execute(text("""
            UPDATE politicos SET ideologia_eco=:eco, ideologia_soc=:soc, ideologia_aut=:aut, ideologia_amb=:amb, ideologia_est=:est, embedding_ideologia=:emb, updated_at = NOW()
            WHERE id = :pid
        """), {"eco": final["eco"], "soc": final["soc"], "aut": final["aut"], "amb": final["amb"], "est": final["est"], "emb": emb, "pid": pid})
        updated += 1
    session.commit()
    return updated

async def ingest_zip(upload_file: UploadFile) -> Dict[str, int]:
    content = await upload_file.read()
    try:
        z = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    names = z.namelist()
    session = SessionLocal()
    try:
        if EXPECTED["politicos"] not in names:
            raise HTTPException(status_code=400, detail="politicos.json required in zip")
        politicos_bytes = z.read(EXPECTED["politicos"])
        politicos_list = json.loads(politicos_bytes.decode("utf-8"))
        inserted_politicos = ingest_politicos(session, politicos_list)

        if EXPECTED["documentos"] in names:
            documentos_bytes = z.read(EXPECTED["documentos"])
            documentos_list = json.loads(documentos_bytes.decode("utf-8"))
            ingest_documentos(session, documentos_list)

        votacoes_map: Dict[str, str] = {}
        if EXPECTED["votacoes"] in names:
            votacoes_map = ingest_votacoes_csv(session, z.read(EXPECTED["votacoes"]))

        if EXPECTED["votos"] in names:
            ingest_votos_csv(session, z.read(EXPECTED["votos"]), votacoes_map)

        docs_emb_count = compute_document_embeddings(session)
        classified = classify_votacoes(session)
        scores_updated = compute_scores(session)
        return {
            "politicos_ingest": len(inserted_politicos),
            "documentos_embedded": docs_emb_count,
            "votacoes_classified": classified,
            "politicos_scores_updated": scores_updated
        }
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("DB error during ingest: %s", e)
        raise HTTPException(status_code=500, detail="DB error during ingest")
    finally:
        session.close()
