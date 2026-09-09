from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path
from typing import List
import sqlite3
import json
import urllib.parse
import os

from backend.ingestion.extract import process_document
from backend.retrieval.search import answer_query

# --------------------------------
# APP
# --------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------
# ENV
# --------------------------------
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

DOCUMENTS_FOLDER = BASE_DIR / "documents" / "processed"

# --------------------------------
# MODELS
# --------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str
    history: List[ChatMessage] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: str
    password: str


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "NSRIT Exam Cell Chatbot API is running live on Render",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------
# CHAT
# --------------------------------
def build_source_payload(source: dict, request: Request):
    file_path = source.get("path")
    filename = source.get("filename") or (Path(file_path).name if file_path else None)

    url = None
    if filename:
        encoded_filename = urllib.parse.quote(filename)
        base_url = str(request.base_url).rstrip("/")
        url = f"{base_url}/download?file={encoded_filename}"

    return {
        "doc_id": source.get("doc_id"),
        "filename": filename,
        "url": url,
        "snippet": source.get("snippet"),
        "confidence": round(float(source.get("match_score", 0) or 0), 2),
        "semester": source.get("semester"),
        "exam_type": source.get("exam_type"),
    }


@app.post("/chat")
def chat(data: ChatRequest, request: Request):
    try:
        history = [
            {"role": item.role, "content": item.content}
            for item in data.history
            if item.content and item.role in {"user", "assistant"}
        ]

        try:
            answer, sources = answer_query(data.prompt, history=history)
        except TypeError:
            # Backward-compatible fallback if search.py still uses old function signature
            answer, sources = answer_query(data.prompt)

    except Exception as e:
        return {
            "answer": f"⚠️ The chatbot encountered an error. {str(e)}",
            "source": None,
            "sources": []
        }

    serialized_sources = [
        build_source_payload(source, request)
        for source in (sources or [])
    ]

    return {
        "answer": answer,
        "source": serialized_sources[0] if serialized_sources else None,
        "sources": serialized_sources
    }


# --------------------------------
# LOGIN
# --------------------------------
@app.post("/examcell/login")
def login(data: LoginRequest):
    if data.email == "examcell@nsrit.edu.in" and data.password == "examcell@nsrit":
        return {"success": True}
    return {"success": False}


@app.post("/examcell/logout")
def logout():
    return {"success": True}


# --------------------------------
# CLEAR
# --------------------------------
@app.post("/examcell/clear")
def clear():
    kb_dir = BASE_DIR / "knowledge_base"
    original_dir = BASE_DIR / "documents" / "original"
    processed_dir = BASE_DIR / "documents" / "processed"

    def clear_files_only(base_dir):
        if not base_dir.exists():
            return
        for root, _, files in os.walk(base_dir):
            for file in files:
                try:
                    os.remove(Path(root) / file)
                except OSError:
                    pass

    # clear uploaded docs
    clear_files_only(original_dir)
    clear_files_only(processed_dir)

    # remove sqlite db
    db_path = kb_dir / "db.sqlite3"
    if db_path.exists():
        os.remove(db_path)

    # reset documents.json
    doc_json = kb_dir / "documents.json"
    if doc_json.exists():
        doc_json.write_text("{}")

    # reset chunks.json
    chunks_json = kb_dir / "chunks.json"
    if chunks_json.exists():
        chunks_json.write_text("{}")

    # remove chroma vector DB
    chroma_dir = kb_dir / "chroma"
    if chroma_dir.exists():
        import shutil
        shutil.rmtree(chroma_dir)

    # recreate chroma folder
    chroma_dir.mkdir(parents=True, exist_ok=True)

    return {"success": True}


# --------------------------------
# UPLOAD
# --------------------------------
def find_existing_subpath(base: Path, tokens):
    cur = base
    for tok in tokens:
        tok_clean = tok.strip()
        if not tok_clean:
            break

        matched = None
        for child in cur.iterdir():
            if child.is_dir() and child.name.lower() == tok_clean.lower():
                matched = child
                break

        if matched is None:
            break

        cur = matched

    return cur


@app.post("/examcell/upload")
async def upload(
    files: List[UploadFile] = File(...),
    dpi: int = Form(300),
    force_ocr: bool = Form(False)
):
    original_dir = BASE_DIR / "documents" / "original"
    processed_dir = BASE_DIR / "documents" / "processed"

    original_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    uploaded_docs = []

    for file in files:
        # split filename tokens
        stem = Path(file.filename).stem
        tokens = stem.split("_")

        # find correct subfolder
        target_dir = find_existing_subpath(original_dir, tokens)

        file_path = target_dir / file.filename

        # prevent overwriting existing files
        if file_path.exists():
            i = 1
            while True:
                candidate = target_dir / f"{Path(file.filename).stem}_{i}{Path(file.filename).suffix}"
                if not candidate.exists():
                    file_path = candidate
                    break
                i += 1

        # save file
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # mirror processed folder
        rel = file_path.parent.relative_to(original_dir)
        processed_target_dir = processed_dir / rel
        processed_target_dir.mkdir(parents=True, exist_ok=True)

        # run ingestion
        doc_id = process_document(
            file_path,
            processed_target_dir,
            dpi=dpi,
            force_ocr=force_ocr
        )

        if doc_id:
            uploaded_docs.append({
                "filename": file.filename,
                "doc_id": doc_id
            })
        else:
            uploaded_docs.append({
                "filename": file.filename,
                "error": "Document ingestion failed"
            })

    return {
        "success": True,
        "documents": uploaded_docs
    }


# --------------------------------
# STATS
# --------------------------------
@app.get("/examcell/stats")
def stats():
    kb_dir = BASE_DIR / "knowledge_base"
    doc_meta = kb_dir / "documents.json"

    metadata = json.loads(doc_meta.read_text()) if doc_meta.exists() else {}
    num_documents = len(metadata)

    db_path = kb_dir / "db.sqlite3"
    num_chunks = 0

    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM chunks")
            num_chunks = cur.fetchone()[0]
        except sqlite3.Error:
            num_chunks = 0
        finally:
            conn.close()

    return {"documents": num_documents, "chunks": num_chunks}


# --------------------------------
# DOWNLOAD
# --------------------------------
@app.get("/download")
def download(file: str):
    decoded_filename = os.path.basename(
        urllib.parse.unquote(file)
    )

    allowed_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
    }

    ext = Path(decoded_filename).suffix.lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    search_folders = [
        BASE_DIR / "documents" / "processed",
        BASE_DIR / "documents" / "original",
    ]

    for folder in search_folders:
        if folder.exists():
            for file_path in folder.rglob(decoded_filename):
                if file_path.is_file():
                    return FileResponse(
                        path=file_path,
                        filename=file_path.name,
                        media_type=allowed_types[ext]
                    )

    raise HTTPException(status_code=404, detail="File not found")



@app.get("/examcell/document/{doc_id}")
def get_document_chunks(doc_id: str):
    db_path = BASE_DIR / "knowledge_base" / "db.sqlite3"

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute(
        "SELECT chunk_idx, text FROM chunks WHERE doc_id=? ORDER BY chunk_idx",
        (doc_id,)
    )

    rows = cur.fetchall()
    conn.close()

    chunks = [
        {"chunk_index": r[0], "text": r[1]}
        for r in rows
    ]

    return {
        "doc_id": doc_id,
        "chunks": chunks
    }
