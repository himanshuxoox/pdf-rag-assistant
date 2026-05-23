import os 
from fastapi import FastAPI , UploadFile , File ,Form, BackgroundTasks,HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from openai import OpenAI
from typing import List, Optional
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# NEW: These are the tools we need to talk to PostgreSQL
from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector
import uuid
import logging

#=============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
#==============================



# ==========================================
# ZONE 1: THE SETUP & CONFIGURATION
# ==========================================
app = FastAPI(title="AI Doucument Processing API")

# Enable Cors form react js front end

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

# ==========================================
# ZONE 2: THE REAL DATABASE (POSTGRES)
# ==========================================
# We replaced DB_MOCK with a real database connection!
# IMPORTANT: Update "password" and "5332" to match your actual local Postgres setup.
# Change this:
DATABASE_URL = "postgresql://postgres:himanshu@localhost:5432/aidoc_db"

# To this:
#DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5332/aidoc_db")

# The "Engine" is what physically connects Python to your Postgres database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Here we define the exact "Blueprint" for our database table.
# Every time someone uploads a PDF, it creates a new row with these columns.
class DocumentModel(Base):
    __tablename__ = "processed_documents"

    id = Column(String(50), primary_key=True)       # chunk-level ID, e.g. doc_3a9f2c1b_chunk_0
    doc_id = Column(String(50), nullable=False)      # parent document ID (new)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), default="processing")
    raw_text = Column(Text, nullable=True)           # text of THIS chunk only
    summary = Column(Text, nullable=True)            # only on chunk_0 (the summary row)
    embedding = Column(Vector(384), nullable=True)
    
    # THE MAGIC: pgvector allows us to store the 384 math numbers right in the database!
    embedding = Column(Vector(384), nullable=True) 

# This line tells Python: "Go look at Postgres. If this table doesn't exist yet, build it now."
Base.metadata.create_all(bind=engine)

#======================
# ZONE 3: THE AI BRAINS
# ==========================================
# Brain 1: The "Librarian" (Creates the 384-number Vectors)

# Initialize the local embedding model (runs entirely on your CPU/GPU)
# 'all-MiniLM-L6-v2' is lightning fast, lightweight, and great for search
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

#Initialize OpenAI Client
#Expects openia_api_key to set in .env
load_dotenv(override=True)

api_key = os.getenv("GROQ_API_KEY")
print("Key loaded:", bool( api_key))

client =  OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key= api_key
)

# #Dummy data base

# DB_MOCK ={}

# #-- Pydantic schemas--

# ==========================================
# ZONE 4: THE SCHEMAS
# ==========================================

class ChatMessage(BaseModel):
    role: str      # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    document_id: str
    message: str
    history: list[ChatMessage] = []  # full conversation so far

# class SearchQuery(BaseModel):
#     query: str
#     search_type: str = "text" # "text" or "vector"
#-- Background Worker Tasks--

# ==========================================
# ZONE 5: THE HEAVY LIFTING (BACKGROUND TASK)
# ==========================================

# def process_document_task(doc_id: str, raw_text: str):
#     """
#     Background task to clean text, generate a summary, and create embedding
#     without blocking the main APi responce thred.
#     """
    
#     try:
#         #1.clean the text(Simaple emample, can be expanded)
#         cleaned_text = " ".join(raw_text.split())
#         DB_MOCK[doc_id]["text"] = cleaned_text

#         print("cleaned_text-->>>",cleaned_text)

#         #2. AI call : Summarization

#         summary_response = client.chat.completions.create(
#             model="openai/gpt-oss-20b", 
#             messages=[
#                 {"role": "system", "content": "You are an expert research assistant. Provide a concise summary and key bullet points for the following text."},
#                 {"role": "user", "content": cleaned_text[:12000]} # Naive token capping for safety
#                 ]
#                 )
#         summary = summary_response.choices[0].message.content
#         print("summary/reaponces from ai-->>",summary)
#         DB_MOCK[doc_id]["summary"] = summary

#         #3. AI Call : Generate Embedding (for future PostgreSQl pgvector search)

#         # embedding_response = client.embeddings.create(
#         #    #model="text-embedding-3-large",
#         #     model= "openai/gpt-oss-20b",
#         #     input=[cleaned_text[:4000]]
#         # )

#         # vector = embedding_response.data[0].embedding
#         # DB_MOCK[doc_id]["embedding"] = vector # Ready to store in pgvector

#         # ALTERNATIVE: Local Vector Generation
#         # This converts text into a 384-dimensional array automatically
#         local_vector = embedding_model.encode(cleaned_text[:4000]).tolist()
#         DB_MOCK[doc_id]["embedding"] = local_vector
#         # update status
#         DB_MOCK[doc_id]["status"]="completed"
#         print(f"Successsfully processed document {doc_id}")
#     except Exception as e:
#         DB_MOCK[doc_id]["status"] = f"failed: {str(e)}"

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits text into overlapping chunks.
    chunk_size = how many words per chunk
    overlap    = how many words to repeat at the start of the next chunk
                 (so sentences at boundaries aren't lost)
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap  # step forward, but repeat 'overlap' words

    return chunks

def process_document_task(doc_id: str, raw_text: str):
    """
    Background task to clean text, generate a summary, and create embedding
    without blocking the main APi responce thred.
    """
    # Open a temporary connection (session) to the database
    db = SessionLocal()
    
    try:
        # Step 1: Clean text
        cleaned_text = " ".join(raw_text.split())

        # Step 2: Ask the AI to summarize
        summary_response = client.chat.completions.create(
            model="openai/gpt-oss-20b", 
            messages=[
                {"role": "system", "content": "You are an expert research assistant. Provide a concise summary and key bullet points for the following text."},
                {"role": "user", "content": cleaned_text[:12000]} 
            ]
        )
        summary = summary_response.choices[0].message.content

        # Split into chunks
        chunks = chunk_text(cleaned_text, chunk_size=500, overlap=50)
        print(f"Document {doc_id} split into {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            vector = embedding_model.encode(chunk).tolist()

            chunk_doc = DocumentModel(
                id=chunk_id,
                doc_id=doc_id,                          # link back to parent
                filename=db.query(DocumentModel)
                           .filter(DocumentModel.id == doc_id)
                           .first().filename,
                status="completed",
                raw_text=chunk,
                summary=summary if i == 0 else None,    # summary only on first chunk
                embedding=vector
            )
            db.add(chunk_doc)

        # Mark the original placeholder row as completed too
        original = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if original:
            original.status = "completed"
            original.summary = summary

        db.commit()
        print(f"Stored {len(chunks)} chunks for {doc_id}")

    except Exception as e:
        doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if doc:
            doc.status = f"failed: {str(e)}"
            db.commit()
    finally:
        db.close()

# ==========================================
# ZONE 6: THE API ENDPOINTS
# ==========================================

# @app.post("/upload")
# async def upload_document(
#     background_tasks: BackgroundTasks,
#     file: UploadFile = File(...)
# ):
#     """
#     Accepts a PDF file, immediately extracts raw text, schedules AI heavy-lifting 
#     in the background, and returns an ID to the frontend.
#     """
#     filename_lower = file.filename.lower()
#     if not filename_lower.endswith('.pdf'):
#         raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
#     try:
#         #Extract text quickly using pypdf
#         pdf_reader = PdfReader(file.file)
#         raw_text = ""
#         for page in pdf_reader.pages:
#             page_text = page.extract_text()
#             if page_text:
#                 raw_text += page_text + "\n"
#         print("raw_text--->>>>>>>>>",raw_text)
#         if not raw_text.strip():
#             raise HTTPException(status_code=400, detail="Could not extract text from this PDF.")
        
#         # Create a unique document tracker
#         doc_id = f"doc_{len(DB_MOCK) + 1}"
#         DB_MOCK[doc_id] = {
#             "filename": file.filename,
#             "status": "processing",
#             "text": None,
#             "summary": None,
#             "embedding": None
#         }

#         print("DB_MOCK--->>",DB_MOCK)

#         # Hand off AI calls to background tasks so frontend doesn't hang/timeout
#         print("Hand off AI calls to background tasks so frontend doesn't hang/timeout")
#         background_tasks.add_task(process_document_task, doc_id, raw_text)

#         return {"document_id": doc_id, "status": "processing", "message": "File uploaded and processing started."}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    db = SessionLocal()
    try:
        pdf_reader = PdfReader(file.file)
        raw_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
        
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from this PDF.")
        
        # Create a unique ID based on how many documents are already in Postgres
        # doc_count = db.query(DocumentModel).count()
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        logger.info(f"doc_id--->>> {doc_id}")
        
        # Create a brand new row in Postgres (It will be mostly empty until the background task finishes)
        new_doc = DocumentModel(id=doc_id, doc_id=doc_id, filename=file.filename, status="processing")
        db.add(new_doc)
        db.commit()

        background_tasks.add_task(process_document_task, doc_id, raw_text)

        return {"document_id": doc_id, "status": "processing", "message": "File uploaded and processing started."}
    finally:
        db.close()

# @app.get("/document/{doc_id}")
# async def get_document_status(doc_id: str):
#     """Frontend polls this endpoint to check if summarization is done."""
#     if doc_id not in DB_MOCK:
#         raise HTTPException(status_code=404, detail="Document not found")
#     return DB_MOCK[doc_id]

@app.get("/document/{doc_id}")
async def get_document_status(doc_id: str):
    db = SessionLocal()
    # Ask Postgres: "Find the row where the ID matches what the user asked for"
    db_doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    db.close()
    
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return {
        "id": db_doc.id,
        "filename": db_doc.filename,
        "status": db_doc.status,
        "summary": db_doc.summary
    }



# @app.post("/chat")
# async def chat_with_document(payload: ChatRequest):
#     """Allows the user to ask questions specifically about the uploaded document."""
#     doc_id = payload.document_id
#     if doc_id not in DB_MOCK or DB_MOCK[doc_id]["status"] != "completed":
#         raise HTTPException(status_code=400, detail="Document is not ready or does not exist.")

#     context = DB_MOCK[doc_id]["text"]
#     print("context->>>>",context)
    
#     try:
#         response = client.chat.completions.create(
#             model="openai/gpt-oss-20b",
#             messages=[
#                 {"role": "system", "content": f"You are a helpful assistant. Answer questions based ONLY on the following context:\n\n{context[:12000]}"},
#                 {"role": "user", "content": payload.message}
#             ]
#         )
#         return {"response": response.choices[0].message.content}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/chat")
# async def chat_with_document(payload: ChatRequest):
#     db = SessionLocal()
#     db_doc = db.query(DocumentModel).filter(DocumentModel.id == payload.document_id).first()
#     db.close()

#     if not db_doc or db_doc.status != "completed":
#         raise HTTPException(status_code=400, detail="Document is not ready or does not exist.")

#     # Grab the text directly from Postgres!
#     context = db_doc.raw_text
    
#     try:
#         response = client.chat.completions.create(
#             model="openai/gpt-oss-20b", 
#             messages=[
#                 {"role": "system", "content": f"You are a helpful assistant. Answer questions based ONLY on the following context:\n\n{context[:12000]}"},
#                 {"role": "user", "content": payload.message}
#             ]
#         )
#         return {"response": response.choices[0].message.content}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_with_document(payload: ChatRequest):
    db = SessionLocal()
    db_doc = db.query(DocumentModel).filter(DocumentModel.id == payload.document_id).first()
    db.close()

    if not db_doc or db_doc.status != "completed":
        raise HTTPException(status_code=400, detail="Document is not ready or does not exist.")

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    context = db_doc.summary or db_doc.raw_text  # use summary as context for efficiency

    # Build the messages list: system + history + new question
    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant. Answer questions based ONLY on the following document context:\n\n{context[:8000]}"
        }
    ]

    # Add previous conversation turns
    for turn in payload.history[-10:]:  # keep last 10 turns to avoid token overflow
        messages.append({"role": turn.role, "content": turn.content})

    # Add the new question
    messages.append({"role": "user", "content": payload.message})

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# @app.post("/search")
# async def search_documents(payload: SearchQuery):
#     """
#     Placeholder endpoint for search. 
#     In production, this executes PostgreSQL full-text queries or pgvector cosine similarity.
#     """
#     if payload.search_type == "text":
#         # Production query placeholder: 
#         # SELECT id, ts_rank(to_tsvector(text), to_tsquery('query')) FROM documents;
#         return {"message": f"Executed Full-Text Search for: '{payload.query}'"}
#     else:
#         # Production query placeholder: 
#         # SELECT id FROM documents ORDER BY embedding <=> '[vector]' LIMIT 5;
#         return {"message": f"Executed Vector Similarity Search for: '{payload.query}'"}

# ==========================================
# ZONE 7: VECTOR SIMILARITY SEARCH
# ==========================================
class SearchQuery(BaseModel):
    query: str
    limit: int = 3 # How many results to return

# @app.post("/search")
# async def search_documents(payload: SearchQuery):
#     db = SessionLocal()
    
#     try:
#         # Step 1: Turn the user's question into a math vector
#         # We use the exact same "Librarian" AI model we used when saving the PDF
#         question_vector = embedding_model.encode(payload.query).tolist()
        
#         # Step 2: Ask Postgres to find the closest matches
#         # The `<=>` operator is pgvector's symbol for "Cosine Similarity Distance"
#         # We order by this distance, so the most relevant documents come first.
#         results = db.query(DocumentModel).order_by(
#             DocumentModel.embedding.cosine_distance(question_vector)
#         ).limit(payload.limit).all()
        
#         # Step 3: Format the response so the frontend can read it easily
#         formatted_results = []
#         for doc in results:
#             formatted_results.append({
#                 "document_id": doc.id,
#                 "filename": doc.filename,
#                 "summary": doc.summary,
#                 # We do NOT send the vector back to the frontend, it's just giant list of numbers!
#             })
            
#         return {"results": formatted_results}
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         db.close()

@app.post("/search")
async def search_documents(payload: SearchQuery):
    db = SessionLocal()
    try:
        question_vector = embedding_model.encode(payload.query).tolist()

        # Search across all chunks
        results = db.query(DocumentModel).filter(
            DocumentModel.doc_id != None  # only chunk rows, not placeholder
        ).order_by(
            DocumentModel.embedding.cosine_distance(question_vector)
        ).limit(payload.limit * 3).all()  # fetch more, then deduplicate

        # Deduplicate: keep only the best chunk per document
        seen_docs = {}
        for chunk in results:
            parent = chunk.doc_id or chunk.id
            if parent not in seen_docs:
                seen_docs[parent] = chunk

        formatted = []
        for doc in list(seen_docs.values())[:payload.limit]:
            formatted.append({
                "document_id": doc.doc_id,
                "filename": doc.filename,
                "summary": doc.summary or doc.raw_text[:200] + "...",
            })

        return {"results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)