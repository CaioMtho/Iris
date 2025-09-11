import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np
import torch
from typing import Optional, Sequence

load_dotenv()

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))
NUM_THREADS = int(os.getenv("OMP_NUM_THREADS", "4"))

torch.set_num_threads(NUM_THREADS)
torch.set_num_interop_threads(NUM_THREADS)

_model: Optional[SentenceTransformer] = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model

def _to_numpy(x) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    if hasattr(x, "cpu") and hasattr(x, "numpy"):  # torch.Tensor
        return x.cpu().numpy()
    if isinstance(x, list):
        arrs = []
        for el in x:
            if hasattr(el, "cpu") and hasattr(el, "numpy"):
                arrs.append(el.cpu().numpy())
            else:
                arrs.append(np.asarray(el))
        try:
            return np.vstack(arrs)
        except Exception:
            return np.asarray(arrs)
    return np.asarray(x)

def embed_texts(texts: Sequence[str], batch_size: int = BATCH_SIZE) -> np.ndarray:
    if not texts:
        return np.zeros((0, 768), dtype=np.float32)
    model = get_model()
    raw = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=False,
        device="cpu"
    )
    arr = _to_numpy(raw)
    if arr.dtype != np.float32:
        arr = arr.astype(np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr
