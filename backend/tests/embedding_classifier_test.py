#!/usr/bin/env python3
"""
Testar embeddings e classifier.

Uso:
  python backend/tests/embedding_classifier_test.py "Minha frase de teste"
Se não passar frase, o script pede input.
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from backend.ml.embeddings import embed_texts
from backend.ml.classifier import make_axis_matrix, classify_texts_batch, classify_single

def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = input("Frase para teste (ex: 'Reduzir impostos para PMEs'): ").strip()
        if not text:
            print("Nenhuma frase informada. Saindo.")
            return

    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "8"))

    print(f"Gerando embedding para: {text!r} (batch_size={batch_size})")
    emb = embed_texts([text], batch_size=batch_size) 
    print("embedding.shape:", emb.shape)
    # imprimir os primeiros 10 elementos para verificação
    first = emb[0].tolist()
    preview = ", ".join(f"{v:.6f}" for v in first[:10])
    print("embedding preview (primeiros 10):", preview)

    axis_matrix, axis_keys = make_axis_matrix(batch_size=batch_size)
    eixo, conf = classify_single(text, axis_matrix=axis_matrix, axis_keys=axis_keys, batch_size=batch_size)
    print(f"classificação: eixo={eixo!r}, confiança={conf:.3f}")

if __name__ == "__main__":
    main()
