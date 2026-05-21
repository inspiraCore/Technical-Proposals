import os
import re
import hashlib
from pathlib import Path
from typing import List, Tuple

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_EXTRACTED_DIR = PROJECT_ROOT / "DATA" / "DATA_EXTRACTED"
RFP_DIR = DATA_EXTRACTED_DIR / "RFPs"
TP_DIR = DATA_EXTRACTED_DIR / "Technical_Proposals"

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "inspira_chunks_v1")

REINDEX = False
CHUNK_CHARS = 700
BATCH = 128
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")


def extract_id(filename: str) -> int:
    m = re.search(r"(\d+)", filename)
    if not m:
        raise ValueError(f"Could not extract numeric ID from filename: {filename}")
    return int(m.group(1))


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def split_to_chunks(text: str, max_chars: int = 700) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) + 1 <= max_chars:
            current += ("\n" + p) if current else p
        else:
            if current:
                chunks.append(current.strip())
            if len(p) <= max_chars:
                current = p
            else:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i : i + max_chars].strip())
                current = ""
    if current:
        chunks.append(current.strip())
    return chunks


def stable_point_id(doc_type: str, pair_id: int, file_name: str, chunk_id: int) -> int:
    raw = f"{doc_type}:{pair_id}:{file_name}:{chunk_id}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(raw, digest_size=8).digest(), "big", signed=False)


def discover_txt_files(folder: Path) -> List[Path]:
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Missing folder: {folder}")
    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".txt"]


def init_qdrant(client: QdrantClient, dim: int) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if REINDEX and COLLECTION in existing:
        print(f"REINDEX=True: deleting collection {COLLECTION}")
        client.delete_collection(collection_name=COLLECTION)
        existing.remove(COLLECTION)

    if COLLECTION not in existing:
        print(f"Creating collection: {COLLECTION}")
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    else:
        print(f"Collection already exists: {COLLECTION}")


def embed(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    if not texts:
        return np.zeros((0, model.get_sentence_embedding_dimension()), dtype="float32")
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False).astype("float32")


def main() -> None:
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("RFP_DIR:", RFP_DIR)
    print("TP_DIR:", TP_DIR)
    print("QDRANT_URL:", QDRANT_URL)
    print("COLLECTION:", COLLECTION)
    print("EMBED_MODEL_NAME:", EMBED_MODEL_NAME)

    rfp_files = discover_txt_files(RFP_DIR)
    tp_files = discover_txt_files(TP_DIR)

    print("RFP files found:", len(rfp_files))
    print("TP files found:", len(tp_files))

    if not rfp_files and not tp_files:
        raise RuntimeError("No RFP or TP text files found in DATA_EXTRACTED.")

    print("Loading embedding model...")
    model = SentenceTransformer(EMBED_MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    print("Embedding dimension:", dim)

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    init_qdrant(client, dim)

    records = []
    for path in rfp_files:
        pid = extract_id(path.name)
        text = read_text_file(path)
        for cid, chunk in enumerate(split_to_chunks(text, CHUNK_CHARS)):
            records.append(("rfp", pid, path.name, cid, chunk))
    for path in tp_files:
        pid = extract_id(path.name)
        text = read_text_file(path)
        for cid, chunk in enumerate(split_to_chunks(text, CHUNK_CHARS)):
            records.append(("tp", pid, path.name, cid, chunk))

    print("Total chunks to index:", len(records))

    for start in tqdm(range(0, len(records), BATCH), desc="Upserting to Qdrant"):
        batch = records[start : start + BATCH]
        texts = [r[4] for r in batch]
        vecs = embed(texts, model)
        points = []
        for (doc_type, pid, fname, cid, ch), v in zip(batch, vecs):
            points.append(
                PointStruct(
                    id=stable_point_id(doc_type, pid, fname, cid),
                    vector=v.tolist(),
                    payload={
                        "doc_type": doc_type,
                        "pair_id": int(pid),
                        "file": fname,
                        "chunk_id": int(cid),
                        "text": ch,
                    },
                )
            )
        client.upsert(collection_name=COLLECTION, points=points)

    info = client.get_collection(COLLECTION)
    print("✅ Done. Collection points_count:", info.points_count)
    print("Collection status:", info.status)


if __name__ == "__main__":
    main()
