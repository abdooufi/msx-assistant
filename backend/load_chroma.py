"""
Load msx_data.json into ChromaDB for semantic/vector search.
Migrated from msx_rag_project/load_data.py
Run after scrape.py: python load_chroma.py
"""
import json
import os
import sys
from config import get_settings

settings   = get_settings()
CHUNK_SIZE = 300
MAX_CHARS  = 2000
BATCH_SIZE = 50
JSON_FILE  = "msx_data.json"


def split_into_chunks(text: str) -> list[str]:
    words       = text.split()
    word_chunks = [" ".join(words[i:i+CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE)]
    chunks      = []
    for wc in word_chunks:
        if len(wc) <= MAX_CHARS:
            chunks.append(wc)
        else:
            for i in range(0, len(wc), MAX_CHARS):
                part = wc[i:i+MAX_CHARS].strip()
                if part: chunks.append(part)
    return [c for c in chunks if len(c) > 20]


def load_chroma():
    print("=" * 60)
    print("  ChromaDB Loader — MSX Vector Index Builder")
    print("=" * 60)

    # Load JSON
    if not os.path.exists(JSON_FILE):
        print(f"❌ {JSON_FILE} not found. Run scrape.py first.")
        sys.exit(1)

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)
    print(f"✅ Loaded {len(docs)} pages from {JSON_FILE}")

    # Setup ChromaDB
    print(f"\n🔌 Setting up ChromaDB at: {settings.chroma_db_path}")
    print(f"   Embedding model: {settings.embedding_model}")
    print(f"   Ollama URL: {settings.localai_base_url.replace('/v1','')}")

    try:
        import chromadb
        from chromadb.utils import embedding_functions

        client = chromadb.PersistentClient(path=settings.chroma_db_path)

        embedding_fn = embedding_functions.OllamaEmbeddingFunction(
            url=f"{settings.localai_base_url.replace('/v1','')}/api/embeddings",
            model_name=settings.embedding_model,
        )

        # Fresh collection
        try:
            client.delete_collection(settings.chroma_collection)
            print(f"🗑️  Deleted old collection '{settings.chroma_collection}'")
        except Exception:
            pass

        collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=embedding_fn,
        )

    except ImportError:
        print("❌ chromadb not installed. Run: pip install chromadb")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ChromaDB setup error: {e}")
        sys.exit(1)

    # Build chunks
    all_chunks, all_ids, all_meta = [], [], []
    for doc in docs:
        chunks = split_into_chunks(doc["content"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc.get('coid') or 'static'}_{i}_{abs(hash(doc['url']))}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_meta.append({"url": doc["url"], "coid": str(doc.get("coid") or "")})

    total = len(all_chunks)
    print(f"\n📊 Total chunks: {total}")
    print(f"   Avg size: {sum(len(c) for c in all_chunks)//max(total,1)} chars")
    print(f"   Batch size: {BATCH_SIZE}")

    # Insert batches
    print(f"\n📥 Inserting into ChromaDB...")
    inserted, skipped = 0, 0

    for i in range(0, total, BATCH_SIZE):
        b_docs = all_chunks[i:i+BATCH_SIZE]
        b_ids  = all_ids[i:i+BATCH_SIZE]
        b_meta = all_meta[i:i+BATCH_SIZE]
        batch  = i // BATCH_SIZE + 1
        total_batches = (total - 1) // BATCH_SIZE + 1

        try:
            collection.add(documents=b_docs, ids=b_ids, metadatas=b_meta)
            inserted += len(b_docs)
            print(f"  ✅ Batch {batch}/{total_batches} — {inserted} chunks")
        except Exception as e:
            print(f"  ⚠️ Batch {batch} failed ({e}), trying one by one...")
            for doc, did, meta in zip(b_docs, b_ids, b_meta):
                try:
                    collection.add(documents=[doc], ids=[did], metadatas=[meta])
                    inserted += 1
                except Exception as e2:
                    skipped += 1
                    print(f"    ❌ Skipped: {did[:40]} → {e2}")

    print(f"\n{'='*60}")
    print(f"  ✅ ChromaDB index built!")
    print(f"  📦 Collection : {settings.chroma_collection}")
    print(f"  📁 Path       : {settings.chroma_db_path}")
    print(f"  ✅ Inserted   : {inserted} chunks")
    print(f"  ❌ Skipped    : {skipped} chunks")
    print(f"{'='*60}")
    print("\n✅ RAG ready! The chatbot will now use semantic search.")


if __name__ == "__main__":
    load_chroma()
