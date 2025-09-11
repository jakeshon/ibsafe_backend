

import numpy as np
import os
import faiss
import torch
from functools import lru_cache

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    pipeline,
)

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedder():
    # 맥북 MPS 지원 확인 및 설정
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    
    print(f"임베딩 모델 사용 디바이스: {device}")
    return SentenceTransformer("BAAI/bge-base-en", device=device)

@lru_cache(maxsize=1)
def get_faiss_and_chunks():
    base_idx = "/Users/shon/ws/ws_proj/aicu/ibsafe_serv/vectordb/index"
    base_ck  = "/Users/shon/ws/ws_proj/aicu/ibsafe_serv/vectordb/chunk"
    index_diet = faiss.read_index(os.path.join(base_idx, "ibs_faiss_diet.index"))
    index_sleep = faiss.read_index(os.path.join(base_idx, "ibs_faiss_sleep.index"))
    index_exercise = faiss.read_index(os.path.join(base_idx, "ibs_faiss_exercise.index"))
    chunk_diet = np.load(os.path.join(base_ck, "chunk_texts_diet.npy"), allow_pickle=True)
    chunk_sleep = np.load(os.path.join(base_ck, "chunk_texts_sleep.npy"), allow_pickle=True)
    chunk_exercise = np.load(os.path.join(base_ck, "chunk_texts_exercise.npy"), allow_pickle=True)
    return (
        {"diet": index_diet, "sleep": index_sleep, "exercise": index_exercise},
        {"diet": chunk_diet, "sleep": chunk_sleep, "exercise": chunk_exercise},
    )