import os
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from openai import OpenAI
from typing import List, Optional
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder
from sqlalchemy import create_engine, Column, String, Text, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector
import uuid
import logging
import json
import hashlib

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# ZONE 1: APP SETUP
# ==========================================
app = FastAPI(title="AI Document Processing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# ZONE 2: DATABASE
# ==========================================
DATABASE_URL = "postgresql://postgres:himanshu@localhost:5432/aidoc_db"
# For deployment use:
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/aidoc_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DocumentModel(Base):
    __tablename__ = "processed_documents"

    id         = Column(String(50), primary_key=True)   # chunk id: doc_abc_chunk_0  OR  doc_abc (parent row)
    doc_id     = Column(String(50), nullable=False)      # always the parent doc id
    filename   = Column(String(255), nullable=False)
    status     = Column(String(50), default="processing")
    raw_text   = Column(Text, nullable=True)             # text of THIS chunk (None on parent row)
    summary    = Column(Text, nullable=True)             # full summary stored on parent + chunk_0
    embedding     = Column(Vector(384), nullable=True)      # NOTE: single definition, no duplicate
    content_hash  = Column(String(64), nullable=True, index=True)  # SHA-256 of raw text for dedup


Base.metadata.create_all(bind=engine)

# ── pgvector HNSW index — created once, persists in Postgres ─────────────────
# Without this, every /chat and /search does a full sequential scan across ALL
# chunks — O(n) per query. HNSW gives O(log n) approximate nearest-neighbour
# search, staying fast even at millions of rows.
#
# Parameters:
#   m=16             — connections per node. Higher = better recall, more memory.
#                      16 is the pgvector default and right for most use cases.
#   ef_construction=64 — size of the candidate list during index build.
#                        Higher = better index quality, slower to build. 64 is optimal.
#
# IF EXISTS guard means this is safe to run on every server start — Postgres
# skips creation silently if the index already exists.
# ─────────────────────────────────────────────────────────────────────────────
def create_hnsw_index():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw
            ON processed_documents
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """))
        # Also add a plain B-tree index on doc_id — used in every /chat
        # and /search WHERE clause, speeds up per-doc chunk lookups significantly
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_doc_id
            ON processed_documents (doc_id);
        """))
        conn.commit()
    logger.info("pgvector HNSW index: ready")

try:
    create_hnsw_index()
except Exception as e:
    # Non-fatal — app works without the index, just slower
    logger.warning(f"Could not create HNSW index (pgvector extension may need enabling): {e}")

# ==========================================
# ZONE 3: AI CLIENTS
# ==========================================
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Cross-encoder reranker — scores (query, chunk) pairs for true semantic relevance.
# Runs AFTER vector retrieval to re-order candidates before sending to the LLM.
# Model is ~85MB, loads once at startup, CPU-only inference is fast enough (<300ms).
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

load_dotenv(override=True)
api_key = os.getenv("GROQ_API_KEY")
logger.info(f"Groq key loaded: {bool(api_key)}")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
)

# ==========================================
# ZONE 4: SCHEMAS
# ==========================================
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    document_id: str
    message: str
    history: List[ChatMessage] = []

class SearchQuery(BaseModel):
    query: str
    limit: int = 3

# ==========================================
# ZONE 5: BACKGROUND TASK — PROCESS DOCUMENT
# ==========================================
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def process_document_task(doc_id: str, raw_text: str, filename: str):
    """
    Background task:
      1. Clean text
      2. Generate summary via Groq
      3. Split into overlapping chunks
      4. Embed each chunk and store in Postgres
      5. Mark parent row as completed
    """
    db = SessionLocal()
    try:
        # Step 1: Clean
        cleaned_text = " ".join(raw_text.split())

        # Step 2: Summarise
        summary_response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert research assistant. "
                        "Provide a concise summary followed by the key bullet points for the following text."
                    ),
                },
                {"role": "user", "content": cleaned_text[:12000]},
            ],
        )
        summary = summary_response.choices[0].message.content
        logger.info(f"Summary generated for {doc_id} ({len(summary)} chars)")

        # Step 3: Chunk
        chunks = chunk_text(cleaned_text, chunk_size=500, overlap=50)
        logger.info(f"Document {doc_id} split into {len(chunks)} chunks")

        # Step 4: Embed and store each chunk
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            vector = embedding_model.encode(chunk).tolist()

            chunk_doc = DocumentModel(
                id=chunk_id,
                doc_id=doc_id,
                filename=filename,          # passed in directly — no extra DB query needed
                status="completed",
                raw_text=chunk,
                summary=summary if i == 0 else None,   # summary only on chunk_0
                embedding=vector,
            )
            db.add(chunk_doc)

        # Step 5: Update the parent/placeholder row
        parent = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if parent:
            parent.status = "completed"
            parent.summary = summary         # also store on parent for quick access

        db.commit()
        logger.info(f"Stored {len(chunks)} chunks for {doc_id}")

    except Exception as e:
        logger.error(f"Failed to process {doc_id}: {e}")
        doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if doc:
            doc.status = f"failed: {str(e)}"
            db.commit()
    finally:
        db.close()


# ==========================================
# ZONE 6: UPLOAD & STATUS ENDPOINTS
# ==========================================

@app.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Accept a PDF, extract text, kick off background processing, return doc_id immediately."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    db = SessionLocal()
    try:
        pdf_reader = PdfReader(file.file)
        raw_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])

        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from this PDF.")

        # ── Duplicate detection via SHA-256 content hash ────────────────────
        # Hash the cleaned text (not raw bytes) so minor whitespace diffs in
        # the same PDF don't generate two entries.
        cleaned_for_hash = " ".join(raw_text.split())
        content_hash = hashlib.sha256(cleaned_for_hash.encode()).hexdigest()

        existing = db.query(DocumentModel).filter(
            DocumentModel.content_hash == content_hash,
            DocumentModel.id == DocumentModel.doc_id,   # only check parent rows
        ).first()

        if existing:
            logger.info(f"Duplicate detected: {file.filename} matches {existing.id}")
            return {
                "document_id": existing.id,
                "status": existing.status,
                "message": f"This document was already uploaded as '{existing.filename}'. Loading it instead.",
                "duplicate": True,
            }

        # New document — create parent row and kick off processing
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        logger.info(f"New upload: {file.filename} → {doc_id}")

        parent = DocumentModel(
            id=doc_id,
            doc_id=doc_id,
            filename=file.filename,
            status="processing",
            content_hash=content_hash,
        )
        db.add(parent)
        db.commit()

        background_tasks.add_task(process_document_task, doc_id, raw_text, file.filename)

        return {"document_id": doc_id, "status": "processing", "message": "Upload received, processing started."}
    finally:
        db.close()


@app.get("/document/{doc_id}")
async def get_document_status(doc_id: str):
    """Frontend polls this to check processing status and get summary."""
    db = SessionLocal()
    try:
        doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "summary": doc.summary,
        }
    finally:
        db.close()


# ==========================================
# ZONE 7: CHAT ENDPOINT
# ==========================================

@app.post("/chat")
async def chat_with_document(payload: ChatRequest):
    """
    Answer questions about a document.
    Retrieves ALL chunks for the doc and builds a rich context window.
    """
    db = SessionLocal()
    try:
        # Verify the document exists and is ready
        parent = db.query(DocumentModel).filter(
            DocumentModel.id == payload.document_id,
            DocumentModel.doc_id == payload.document_id,
        ).first()

        if not parent:
            raise HTTPException(status_code=404, detail="Document not found.")
        if parent.status != "completed":
            raise HTTPException(status_code=400, detail=f"Document is not ready yet (status: {parent.status}).")

        if not payload.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty.")

        # ── Stage 1: Vector retrieval — cast a wide net ─────────────────────────
        # Over-fetch (top 20) so the reranker has enough candidates to work with.
        # Cosine similarity is a fast but coarse signal — good for recall, not precision.
        question_vector = embedding_model.encode(payload.message).tolist()

        # Set ef_search=100 for this session — controls how many HNSW nodes are
        # visited during search. Higher = better recall, slower query.
        # 100 is the sweet spot: ~99% recall vs exact search, <5ms overhead.
        db.execute(text("SET hnsw.ef_search = 100"))

        candidates = (
            db.query(DocumentModel)
            .filter(
                DocumentModel.doc_id == payload.document_id,
                DocumentModel.id != payload.document_id,   # exclude parent row
                DocumentModel.raw_text != None,
            )
            .order_by(DocumentModel.embedding.cosine_distance(question_vector))
            .limit(20)   # wide net — reranker will trim this down
            .all()
        )

        # ── Stage 2: Cross-encoder reranking — precision pass ────────────────
        # The cross-encoder reads (question + chunk) together as a single input,
        # giving it full attention over both — far more accurate than dot-product.
        # Returns a relevance score per pair; higher = more relevant.
        if len(candidates) > 1:
            pairs = [(payload.message, c.raw_text) for c in candidates]
            scores = reranker.predict(pairs)
            ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
            relevant_chunks = [chunk for _, chunk in ranked[:5]]   # top 5 after reranking
            logger.info(
                f"Reranker scores for '{payload.message[:40]}': "
                f"top={scores[0]:.3f} bottom={scores[-1]:.3f} kept=5/{len(candidates)}"
            )
        else:
            relevant_chunks = candidates  # only 1 chunk — nothing to rerank

        if relevant_chunks:
            # Label each chunk [1], [2]... so the LLM can cite by number in its answer
            numbered_chunks = []
            sources = []
            for i, c in enumerate(relevant_chunks, 1):
                numbered_chunks.append(f"[{i}] {c.raw_text}")
                # Extract chunk number from id e.g. "doc_abc_chunk_7" -> "Chunk 8"
                chunk_num = c.id.split("_chunk_")[-1] if "_chunk_" in c.id else str(i)
                sources.append({
                    "ref": i,
                    "chunk": f"Chunk {int(chunk_num) + 1}",   # 1-indexed for display
                    "preview": c.raw_text[:160].replace("\n", " ").strip() + "…",
                })
            context = "\n\n---\n\n".join(numbered_chunks)
        else:
            context = parent.summary or ""
            sources = []

        system_prompt = (
            "You are a helpful assistant. Answer questions based ONLY on the numbered document "
            "context below. Where relevant, cite the source using [1], [2] etc. inline in your answer. "
            "If the answer is not in the context, say so clearly.\n\n"
            f"DOCUMENT CONTEXT:\n{context[:10000]}"
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Include last 10 turns of conversation history
        for turn in payload.history[-10:]:
            messages.append({"role": turn.role, "content": turn.content})

        messages.append({"role": "user", "content": payload.message})

        db.close()     # close DB before streaming — don't hold connection during LLM call

        # Stream tokens, then append a JSON citations block after a sentinel marker.
        # Frontend splits on the sentinel to separate answer text from sources.
        CITATION_SENTINEL = "\n\n__CITATIONS__:"

        def token_stream():
            try:
                stream = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=messages,
                    stream=True,
                )
                for chunk in stream:
                    token = chunk.choices[0].delta.content or ""
                    if token:
                        yield token

                # After LLM finishes, append citations so the frontend can render them
                if sources:
                    yield CITATION_SENTINEL + json.dumps(sources)

            except Exception as e:
                logger.error(f"Streaming error for {payload.document_id}: {e}")
                yield f"\n\n[Error: {str(e)}]"

        return StreamingResponse(token_stream(), media_type="text/plain; charset=utf-8")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for {payload.document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Guard: only close if not already closed above (streaming path closes early)
        try:
            db.close()
        except Exception:
            pass


# ==========================================
# ZONE 8: SEARCH ENDPOINT
# ==========================================

@app.post("/search")
async def search_documents(payload: SearchQuery):
    """
    Vector similarity search across all document chunks.
    Returns one result per unique document (best matching chunk).
    """
    db = SessionLocal()
    try:
        question_vector = embedding_model.encode(payload.query).tolist()

        # Set ef_search for this query
        db.execute(text("SET hnsw.ef_search = 100"))

        # Fetch top candidates across all chunks
        results = (
            db.query(DocumentModel)
            .filter(
                DocumentModel.doc_id != None,
                DocumentModel.embedding != None,
                DocumentModel.raw_text != None,   # only real chunk rows
            )
            .order_by(DocumentModel.embedding.cosine_distance(question_vector))
            .limit(payload.limit * 5)             # over-fetch then deduplicate
            .all()
        )

        # Deduplicate — keep only the highest-ranked chunk per document
        seen: dict = {}
        for chunk in results:
            parent_id = chunk.doc_id
            if parent_id not in seen:
                seen[parent_id] = chunk

        formatted = []
        for chunk in list(seen.values())[: payload.limit]:
            # Get full summary from the parent row (most reliable)
            parent = db.query(DocumentModel).filter(
                DocumentModel.id == chunk.doc_id,
                DocumentModel.doc_id == chunk.doc_id,
            ).first()
            full_summary = (parent.summary if parent else None) or chunk.summary or chunk.raw_text[:500]

            formatted.append({
                "document_id": chunk.doc_id,
                "filename": chunk.filename,
                "summary": full_summary,
                "status": parent.status if parent else chunk.status,
            })

        return {"results": formatted}

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ==========================================
# ZONE 9: LIST ALL DOCS & LOAD DOC FOR CHAT
# ==========================================

@app.get("/documents")
async def list_all_documents():
    """Return all unique uploaded documents (parent rows only, one per doc)."""
    db = SessionLocal()
    try:
        docs = (
            db.query(DocumentModel)
            .filter(DocumentModel.id == DocumentModel.doc_id)  # only parent rows
            .order_by(DocumentModel.filename)
            .all()
        )
        return {
            "documents": [
                {
                    "document_id": d.id,
                    "filename": d.filename,
                    "status": d.status,
                    "summary": d.summary or "",
                }
                for d in docs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/load-doc/{doc_id}")
async def load_doc_for_chat(doc_id: str):
    """
    Load a document's metadata by parent doc_id.
    Called when the user switches docs via search results or the Recent list.
    """
    db = SessionLocal()
    try:
        parent = db.query(DocumentModel).filter(
            DocumentModel.id == doc_id,
            DocumentModel.doc_id == doc_id,
        ).first()

        if not parent:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "document_id": doc_id,
            "filename": parent.filename,
            "status": parent.status,
            "summary": parent.summary or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)