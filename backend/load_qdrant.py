"""
Load msx_data.json into Qdrant for semantic/vector search.
Run once (or after re-scraping): python load_qdrant.py

Pipeline:
  msx_data.json → chunk text → embed via Ollama → upsert into Qdrant
"""
import json
import os
import sys
import uuid
import httpx
from config import get_settings

settings   = get_settings()
CHUNK_SIZE = 300   # words per chunk
MAX_CHARS  = 2000
BATCH_SIZE = 50
JSON_FILE  = "msx_data.json"


def split_into_chunks(text: str) -> list[str]:
    words  = text.split()
    chunks = []
    for i in range(0, len(words), CHUNK_SIZE):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        if len(chunk) <= MAX_CHARS:
            chunks.append(chunk)
        else:
            for j in range(0, len(chunk), MAX_CHARS):
                part = chunk[j:j + MAX_CHARS].strip()
                if part:
                    chunks.append(part)
    return [c for c in chunks if len(c) > 20]


def get_embedding(text: str, model: str, base_url: str) -> list[float]:
    """OpenAI-compatible embeddings endpoint (supported by Ollama v0.1.24+)."""
    url = base_url.rstrip("/") + "/embeddings"  # base_url already ends with /v1
    r   = httpx.post(url, json={"model": model, "input": text}, timeout=60)
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def load_qdrant():
    print("=" * 60)
    print("  Qdrant Loader — MSX Vector Index Builder")
    print("=" * 60)

    if not os.path.exists(JSON_FILE):
        print(f"❌ {JSON_FILE} not found. Run scrape.py first.")
        sys.exit(1)

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)
    print(f"✅ Loaded {len(docs)} pages from {JSON_FILE}")

    # Setup Qdrant
    print(f"\n🔌 Connecting to Qdrant at: {settings.qdrant_url}")
    print(f"   Collection  : {settings.qdrant_collection}")
    print(f"   Embed model : {settings.embedding_model}")

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct

        client = QdrantClient(url=settings.qdrant_url, timeout=30)
    except ImportError:
        print("❌ qdrant-client not installed. Run: pip install qdrant-client")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to Qdrant: {e}")
        print(f"   Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")
        sys.exit(1)

    # Probe embedding dimension from first chunk
    print(f"\n🔍 Probing embedding dimension...")
    try:
        sample_vec = get_embedding("test", settings.embedding_model, settings.LOCALAI_BASE_URL)
        dim = len(sample_vec)
        print(f"   Embedding dimension: {dim}")
    except Exception as e:
        print(f"❌ Embedding probe failed: {e}")
        print(f"   Make sure Ollama is running and '{settings.embedding_model}' is pulled.")
        sys.exit(1)

    # Recreate collection
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        client.delete_collection(settings.qdrant_collection)
        print(f"🗑️  Deleted old collection '{settings.qdrant_collection}'")

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    print(f"✅ Created collection '{settings.qdrant_collection}' (dim={dim}, cosine)")

    # Build chunks
    all_chunks, all_meta = [], []
    for doc in docs:
        for chunk in split_into_chunks(doc["content"]):
            all_chunks.append(chunk)
            all_meta.append({"url": doc["url"], "coid": str(doc.get("coid") or "")})

    total = len(all_chunks)
    print(f"\n📊 Total chunks : {total}")
    print(f"   Avg size     : {sum(len(c) for c in all_chunks) // max(total, 1)} chars")
    print(f"   Batch size   : {BATCH_SIZE}")

    # Embed and upsert in batches
    print(f"\n📥 Embedding and inserting into Qdrant...")
    inserted, skipped = 0, 0

    for i in range(0, total, BATCH_SIZE):
        batch_chunks = all_chunks[i:i + BATCH_SIZE]
        batch_meta   = all_meta[i:i + BATCH_SIZE]
        batch_num    = i // BATCH_SIZE + 1
        total_batches = (total - 1) // BATCH_SIZE + 1

        points = []
        for chunk, meta in zip(batch_chunks, batch_meta):
            try:
                vec = get_embedding(chunk, settings.embedding_model, settings.localai_base_url)
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec,
                    payload={"text": chunk, **meta},
                ))
            except Exception as e:
                skipped += 1
                print(f"  ⚠️  Embed failed, skipping chunk: {e}")

        if points:
            try:
                client.upsert(collection_name=settings.qdrant_collection, points=points)
                inserted += len(points)
                print(f"  ✅ Batch {batch_num}/{total_batches} — {inserted} vectors")
            except Exception as e:
                print(f"  ❌ Batch {batch_num} upsert failed: {e}")
                skipped += len(points)

    final_count = client.count(settings.qdrant_collection).count
    print(f"\n{'=' * 60}")
    print(f"  ✅ Qdrant index built!")
    print(f"  📦 Collection : {settings.qdrant_collection}")
    print(f"  🌐 URL        : {settings.qdrant_url}")
    print(f"  ✅ Inserted   : {inserted} vectors")
    print(f"  ❌ Skipped    : {skipped} chunks")
    print(f"  📊 Total live : {final_count} vectors")
    print(f"{'=' * 60}")
    print("\n✅ RAG ready! The chatbot will now use Qdrant semantic search.")


if __name__ == "__main__":
    load_qdrant()
