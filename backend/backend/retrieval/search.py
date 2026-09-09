import json
import uuid
import sqlite3
from pathlib import Path
from typing import List, Optional

import re
import torch

try:
    import chromadb
    CHROMA_AVAILABLE = True
except Exception:
    chromadb = None
    CHROMA_AVAILABLE = False

from sentence_transformers import SentenceTransformer
import numpy as np

from backend.llm.groq_llm import generate_answer


# --------------------------------------------------
# PATHS
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]

KB_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = KB_DIR / "chroma"
DOC_META = KB_DIR / "documents.json"
SQLITE_DB = KB_DIR / "db.sqlite3"
CHUNKS_JSON = KB_DIR / "chunks.json"

KB_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

if not DOC_META.exists():
    DOC_META.write_text("{}")


# --------------------------------------------------
# DOCUMENT METADATA CACHE
# --------------------------------------------------
_DOC_META_CACHE = None
_CHUNKS_CACHE = None



def load_doc_metadata():
    global _DOC_META_CACHE

    if _DOC_META_CACHE is None:
        try:
            _DOC_META_CACHE = json.loads(DOC_META.read_text()) if DOC_META.exists() else {}
        except Exception:
            _DOC_META_CACHE = {}

    return _DOC_META_CACHE

def load_chunk_metadata():
    global _CHUNKS_CACHE

    if _CHUNKS_CACHE is None:
        try:
            _CHUNKS_CACHE = json.loads(CHUNKS_JSON.read_text()) if CHUNKS_JSON.exists() else {}
        except Exception:
            _CHUNKS_CACHE = {}

    return _CHUNKS_CACHE



# --------------------------------------------------
# EMBEDDING MODEL (LAZY LOADED FOR 512MB RAM COMPLIANCE)
# --------------------------------------------------
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

try:
    torch.set_num_threads(1)
except Exception:
    pass


def get_embedding_model():
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
    return _model


# --------------------------------------------------
# SQLITE FALLBACK STORE
# --------------------------------------------------
class SqliteVectorStore:
    def __init__(self, path: Path):
        self.path = str(path)
        self._ensure_db()

    def _ensure_db(self):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                doc_id TEXT,
                year INTEGER,
                semester INTEGER,
                exam_type TEXT,
                chunk_idx INTEGER,
                text TEXT,
                embedding TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def add_chunks(self, doc_id: str, chunks: List[str], embeddings: List[list], meta: dict):
        self._ensure_db()
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            _id = f"{doc_id}_{i}"
            cur.execute(
                """
                INSERT OR REPLACE INTO chunks
                (id, doc_id, year, semester, exam_type, chunk_idx, text, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _id,
                    doc_id,
                    meta.get("year"),
                    meta.get("semester"),
                    meta.get("exam_type"),
                    i,
                    chunk,
                    json.dumps(emb)
                )
            )

        conn.commit()
        conn.close()

    def query(self, query_embedding: List[float], top_k: int = 8, semester=None, doc_type=None):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()

        sql = "SELECT id, doc_id, text, embedding FROM chunks WHERE 1=1"
        params = []

        if semester is not None:
            sql += " AND semester = ?"
            params.append(semester)

        if doc_type is not None:
            sql += " AND exam_type = ?"
            params.append(doc_type)

        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return []

        q = np.array(query_embedding, dtype=float)
        texts = []
        sims = []
        doc_ids = []

        for _id, doc_id, text, emb_json in rows:
            try:
                emb = np.array(json.loads(emb_json), dtype=float)
            except Exception:
                continue

            denom = (np.linalg.norm(q) * np.linalg.norm(emb))
            if denom == 0:
                sim = 0.0
            else:
                sim = float(np.dot(q, emb) / denom)

            texts.append(text)
            sims.append(sim)
            doc_ids.append(doc_id)

        idxs = np.argsort(sims)[::-1][:top_k]
        results = []
        for i in idxs:
            results.append((texts[i], float(sims[i]), doc_ids[i]))

        return results


# Initialize sqlite fallback store
sqlite_store = SqliteVectorStore(SQLITE_DB)


def get_chroma_collection():
    """
    Safely get or create the Chroma collection.
    This is safe to call repeatedly.
    """
    if not CHROMA_AVAILABLE:
        return None

    try:
        client = chromadb.Client(
            chromadb.config.Settings(
                persist_directory=str(CHROMA_DIR),
                anonymized_telemetry=False
            )
        )

        return client.get_or_create_collection(
            name="examcell_docs",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception:
        return None


# --------------------------------------------------
# STORE DOCUMENT
# --------------------------------------------------
def store_document(chunks: List[str], source_path: str, doc_tags: dict = None) -> str:
    """
    Stores chunks into the available vector store and saves source metadata.
    """
    doc_id = str(uuid.uuid4())
    doc_tags = doc_tags or {}

    embeddings = get_embedding_model().encode(chunks).tolist()

    collection = get_chroma_collection()
    if collection is not None:
        try:
            meta = {"doc_id": doc_id}
            meta.update(doc_tags)

            collection.add(
                documents=chunks,
                embeddings=embeddings,
                metadatas=[meta] * len(chunks),
                ids=[f"{doc_id}_{i}" for i in range(len(chunks))]
            )
        except Exception as e:
            print(f"Warning: failed to add to Chroma: {e}")

    try:
        sqlite_store.add_chunks(doc_id, chunks, embeddings, doc_tags)
    except Exception as e:
        print(f"Error: failed to persist chunks to sqlite: {e}")

    try:
        all_chunks = json.loads(CHUNKS_JSON.read_text()) if CHUNKS_JSON.exists() else {}
    except Exception:
        all_chunks = {}

    try:
        all_chunks[doc_id] = [
            {"chunk_index": i, "text": chunks[i]}
            for i in range(len(chunks))
        ]
        CHUNKS_JSON.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Warning: failed to write chunks.json: {e}")

    try:
        metadata = json.loads(DOC_META.read_text()) if DOC_META.exists() else {}
    except Exception:
        metadata = {}

    metadata[doc_id] = {
    "source_path": source_path,
    "filename": Path(source_path).name if source_path else None,
    "year": doc_tags.get("year"),
    "semester": doc_tags.get("semester"),
    "exam_type": doc_tags.get("exam_type"),
    "title": doc_tags.get("title"),
}


    DOC_META.write_text(json.dumps(metadata, indent=2))
    global _DOC_META_CACHE
    _DOC_META_CACHE = metadata

    return doc_id


# --------------------------------------------------
# QUERY HELPERS
# --------------------------------------------------
def normalize_query(query: str) -> str:
    q = (query or "").lower().replace("’", "'")

    q = re.sub(r"([a-zA-Z])([0-9])", r"\1 \2", q)
    q = re.sub(r"([0-9])([a-zA-Z])", r"\1 \2", q)

    roman_semester_patterns = [
        (r"\bviii\s+semester\b", "8 semester"),
        (r"\bvii\s+semester\b", "7 semester"),
        (r"\bvi\s+semester\b", "6 semester"),
        (r"\biv\s+semester\b", "4 semester"),
        (r"\bv\s+semester\b", "5 semester"),
        (r"\biii\s+semester\b", "3 semester"),
        (r"\bii\s+semester\b", "2 semester"),
        (r"\bi\s+semester\b", "1 semester"),
        (r"\bsemester\s+viii\b", "semester 8"),
        (r"\bsemester\s+vii\b", "semester 7"),
        (r"\bsemester\s+vi\b", "semester 6"),
        (r"\bsemester\s+iv\b", "semester 4"),
        (r"\bsemester\s+v\b", "semester 5"),
        (r"\bsemester\s+iii\b", "semester 3"),
        (r"\bsemester\s+ii\b", "semester 2"),
        (r"\bsemester\s+i\b", "semester 1"),
    ]

    for pattern, replacement in roman_semester_patterns:
        q = re.sub(pattern, replacement, q)


    replacements = {
        " sem ": " semester ",
        " sem": " semester",
        "sem ": "semester ",
        "timetble": "timetable",
        "time table": "timetable",
        "supp": "supply",
        "1sem": "1 semester",
        "2sem": "2 semester",
        "3sem": "3 semester",
        "4sem": "4 semester",
        "supplementary": "supply",
        "exam time table": "timetable",
        "reval": "revaluation",
        "hallticket": "hall ticket",
        "what's": "what is",
        "after noon": "afternoon",
        "goodafternoon": "good afternoon",
        "goodmorning": "good morning",
        "goodevening": "good evening",
        "goodnight": "good night",
    }


    for k, v in replacements.items():
        q = q.replace(k, v)

    q = re.sub(r"[_()\[\]{}?!,:;]+", " ", q)
    q = re.sub(r"[^a-z0-9./'\-\s]", " ", q)
    q = re.sub(r"\s+", " ", q)
    return q.strip()

def tokenize_search_text(text: str):
    stop_words = {
        "the", "a", "an", "of", "for", "to", "in", "on", "and", "or",
        "is", "are", "was", "were", "me", "please", "show", "give", "tell",
        "about", "what", "which", "when", "with", "from", "student", "students",
    }
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_query(text))
        if len(token) > 1 and token not in stop_words
    ]


def extract_query_intent(query: str):
    q = normalize_query(query)

    intent = {
        "semester": None,
        "year": None,
        "exam_type": None,
        "document_type": None,
        "topic": None,
        "batch": None,
        "mid_number": None,
        "regulation": None,
        "admitted_batch": None,

    }

    sem_match = re.search(r'\b([1-8])(st|nd|rd|th)?\s*(sem|semester)\b', q)
    if sem_match:
        intent["semester"] = int(sem_match.group(1))

    if intent["semester"] is None:
        sem_match = re.search(r'\b(sem|semester)\s*([1-8])\b', q)
        if sem_match:
            intent["semester"] = int(sem_match.group(2))

    year_patterns = [
        (r"\b1st year\b|\bfirst year\b|\bi year\b|\b1 year\b", 1),
        (r"\b2nd year\b|\bsecond year\b|\bii year\b|\b2 year\b", 2),
        (r"\b3rd year\b|\bthird year\b|\biii year\b|\b3 year\b", 3),
        (r"\b4th year\b|\bfourth year\b|\biv year\b|\b4 year\b", 4),
    ]
    for pattern, year in year_patterns:
        if re.search(pattern, q):
            intent["year"] = year
            break

    if "mid" in q:
        intent["exam_type"] = "MID"
    elif "regular" in q:
        intent["exam_type"] = "REGULAR"
    elif "supply" in q or "supplementary" in q:
        intent["exam_type"] = "SUPPLY"
    elif "revaluation" in q or "reval" in q:
        intent["exam_type"] = "REVALUATION"

    if re.search(r"\bmid\s*1\b|\bmid\s*one\b", q):
        intent["mid_number"] = 1
    elif re.search(r"\bmid\s*2\b|\bmid\s*two\b", q):
        intent["mid_number"] = 2

    if "moocs" in q:
        intent["topic"] = "MOOCS"
    elif "honors" in q or "honor" in q or "minor" in q or "minors" in q or "homi" in q:
        intent["topic"] = "HONORS"
    elif "fsi" in q:
        intent["topic"] = "FSI"
    elif "review" in q:
        intent["topic"] = "REVIEW"

    batch_match = re.search(r"\b(20\d{2})\s*admitted batch\b", q)
    if batch_match:
        intent["batch"] = batch_match.group(1)

    if "timetable" in q or "schedule" in q:
        intent["document_type"] = "TIMETABLE"
    elif "fee" in q:
        intent["document_type"] = "FEE"
    elif "circular" in q:
        intent["document_type"] = "CIRCULAR"
        
    regulation_patterns = [
        (r"\bar\s*20\s*rev\s*1\.0\b|\br\s*20\s*rev\s*1\.0\b", "AR20 REV 1.0"),
        (r"\bar\s*23\b|\br\s*23\b|regulation\s*2023", "AR23"),
        (r"\bar\s*20\b|\br\s*20\b|regulation\s*2020", "AR20"),
        (r"\bar\s*21\b|\br\s*21\b|regulation\s*2021", "AR21"),
    ]
    for pattern, value in regulation_patterns:
        if re.search(pattern, q):
            intent["regulation"] = value
            break

    admitted_batch_match = re.search(r"\b(20\d{2}\s*[-–]\s*20\d{2}|20\d{2})\s*admitted batch\b", q)
    if admitted_batch_match:
        intent["admitted_batch"] = re.sub(r"\s+", "", admitted_batch_match.group(1)).replace("–", "-")


    return intent

def is_identity_query(query: str) -> bool:
    q = normalize_query(query)

    identity_patterns = {
        "your name",
        "what is your name",
        "u r name",
        "ur name",
        "name",
        "who are you",
        "tell me your name",
        "college",
        "college name",
        "what is your college",
        "what is your college name",
        "which college",
        "which institute",
    }

    return q in identity_patterns


def is_general_chat(query: str) -> bool:
    q = normalize_query(query)

    if not q:
        return True

    greeting_patterns = {
        "hello", "hi", "hey", 
        "good", "good morning", "good afternoon", "good evening", "good night",
        "how are you",
        "thanks", "thank you", "ok thanks", "thank you so much",
    }

    off_topic_patterns = {
        "had dinner",
        "have you had dinner",
        "u had dinner",
        "did you have dinner",
        "dinner",
        "had lunch",
        "u had lunch",
        "lunch",
        "how was your day",
        "what are you doing",
    }

    if q in greeting_patterns or q in off_topic_patterns:
        return True

    if is_identity_query(q):
        return True

    if "established" in q and ("nsrit" in q or "college" in q or "institute" in q):
        return True

    if re.fullmatch(r"(it|its|it's)?\s*\d{4}", q):
        return True

    return False



def is_title_like_query(query: str) -> bool:
    q = normalize_query(query)
    title_patterns = [
        "semester end examination",
        "mid - examination",
        "mid examination",
        "review schedule",
        "examination schedule",
        "office of the controller of examinations",
    ]
    return any(pattern in q for pattern in title_patterns)




def build_retrieval_query(query: str, history: Optional[list] = None) -> str:
    """
    Helps follow-up questions work better.
    If user asks a short follow-up like 'what about supply?' we combine it
    with recent user context.
    """
    history = history or []
    current = query.strip()

    if not current:
        return query

    normalized_current = normalize_query(current)
    
    if is_general_chat(normalized_current):
        return query

    if normalized_current in {"honor and minor", "honors and minors", "honor minor", "minor honor"}:
        return query

    if any(word in normalized_current for word in ["moocs", "fsi", "review", "honors", "minor", "mid 1", "mid 2"]):
        return query


    # Do not attach previous retrieval context to pure corrections/general replies
    if re.fullmatch(r"(it|its|it's)?\s*\d{4}", normalized_current):
        return query

    if "established" in normalized_current and (
        "nsrit" in normalized_current or "college" in normalized_current or "institute" in normalized_current
    ):
        return query

    short_follow_up = (
        len(current.split()) <= 8
        or current.lower().startswith(("what about", "and ", "also", "same", "then", "that", "this"))
    )

    if not short_follow_up:
        return query

    recent_user_messages = [
        item.get("content", "").strip()
        for item in history
        if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
    ]

    if not recent_user_messages:
        return query

    prefix = " ".join(recent_user_messages[-2:]).strip()
    if not prefix:
        return query

    combined = f"{prefix} {current}".strip()
    return combined


def build_filename_label(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"\s+", " ", stem.replace("_", " ")).strip().lower()


def is_generic_doc_title(title: Optional[str]) -> bool:
    clean_title = (title or "").strip().lower()
    if not clean_title:
        return True

    generic_markers = {
        "office of the controller of examinations",
        "controller of examinations",
        "copyto",
    }
    if any(marker in clean_title for marker in generic_markers):
        return True

    if re.fullmatch(r"[\d\s:/().-]+", clean_title):
        return True

    words = re.findall(r"[a-z0-9]+", clean_title)
    if len(words) < 4:
        return True

    if len(set(words)) <= 2:
        return True

    return False


def extract_reference_metadata(reference: str) -> dict:
    raw = (reference or "").lower()
    compact = re.sub(r"[^a-z0-9]+", "", raw)
    spaced = re.sub(r"[^a-z0-9]+", " ", raw)

    year = None
    for token, value in [("ivyear", 4), ("iiiyear", 3), ("iiyear", 2), ("iyear", 1)]:
        if token in compact:
            year = value
            break

    if year is None:
        if re.search(r"\b4th year\b|\bfourth year\b", spaced):
            year = 4
        elif re.search(r"\b3rd year\b|\bthird year\b", spaced):
            year = 3
        elif re.search(r"\b2nd year\b|\bsecond year\b", spaced):
            year = 2
        elif re.search(r"\b1st year\b|\bfirst year\b", spaced):
            year = 1

    sem_in_year = None
    for token, value in [("iisem", 2), ("isem", 1)]:
        if token in compact:
            sem_in_year = value
            break

    semester = None
    if year is not None and sem_in_year is not None:
        semester = (year - 1) * 2 + sem_in_year

    if semester is None:
        sem_match = re.search(r"\b([1-8])(st|nd|rd|th)?\s*(sem|semester)\b", spaced)
        if sem_match:
            semester = int(sem_match.group(1))
        else:
            sem_match = re.search(r"\b(sem|semester)\s*([1-8])\b", spaced)
            if sem_match:
                semester = int(sem_match.group(2))

    exam_type = None
    if "revaluation" in compact:
        exam_type = "REVALUATION"
    elif "supplementary" in compact or "supply" in compact:
        exam_type = "SUPPLY"
    elif "regular" in compact:
        exam_type = "REGULAR"
    elif "mid" in compact:
        exam_type = "MID"
    elif "fee" in compact:
        exam_type = "FEE"
    elif "honors" in compact or "minor" in compact or "homi" in compact:
        exam_type = "HONORS"
    elif "timetable" in compact or "schedule" in compact:
        exam_type = "TIMETABLE"

    topic = None
    if "moocs" in compact:
        topic = "MOOCS"
    elif "honors" in compact or "minor" in compact or "homi" in compact:
        topic = "HONORS"
    elif "fsi" in compact:
        topic = "FSI"
    elif "review" in compact:
        topic = "REVIEW"

    mid_number = None
    if re.search(r"\bmid\s*(1|one)\b", spaced):
        mid_number = 1
    elif re.search(r"\bmid\s*(2|two)\b", spaced):
        mid_number = 2

    return {
        "year": year,
        "semester": semester,
        "exam_type": exam_type,
        "topic": topic,
        "mid_number": mid_number,
    }


def combine_doc_text(doc_info: dict, chunk_text: str = "") -> str:
    return " ".join(
        part for part in [
            doc_info.get("title"),
            doc_info.get("filename"),
            doc_info.get("path"),
            chunk_text,
        ]
        if part
    ).lower()

def get_doc_info(doc_id: str):
    meta = load_doc_metadata()
    info = meta.get(doc_id, {}) if isinstance(meta, dict) else {}

    path = info.get("source_path") if isinstance(info, dict) else None
    filename = info.get("filename") if isinstance(info, dict) else None
    if not filename and path:
        filename = Path(path).name

    title = info.get("title") if isinstance(info, dict) else None
    if is_generic_doc_title(title) and filename:
        title = build_filename_label(filename)

    inferred = extract_reference_metadata(" ".join(filter(None, [path or "", filename or "", title or ""])))

    inferred_exam_type = inferred.get("exam_type")
    stored_exam_type = info.get("exam_type") if isinstance(info, dict) else None
    if inferred_exam_type == "TIMETABLE" and stored_exam_type in {"MID", "SUPPLY", "REVALUATION", "REGULAR", "HONORS"}:
        exam_type = stored_exam_type
    else:
        exam_type = inferred_exam_type or stored_exam_type

    return {
        "doc_id": doc_id,
        "filename": filename,
        "path": path,
        "year": inferred.get("year") or (info.get("year") if isinstance(info, dict) else None),
        "semester": inferred.get("semester") or (info.get("semester") if isinstance(info, dict) else None),
        "exam_type": exam_type,
        "title": title,
        "topic": inferred.get("topic"),
        "mid_number": inferred.get("mid_number"),
    }

def has_explicit_semester_match(text: str, semester: int) -> bool:
    normalized = normalize_query(text)
    return bool(
        re.search(rf"\b{semester}(st|nd|rd|th)?\s*(sem|semester)\b", normalized)
        or re.search(rf"\b(sem|semester)\s*{semester}\b", normalized)
    )


def document_matches_intent(doc_id: str, chunk_text: str, intent: dict) -> bool:
    doc_info = get_doc_info(doc_id)
    combined = normalize_query(combine_doc_text(doc_info, chunk_text))
    exam_type = (doc_info.get("exam_type") or "").upper()
    semester = doc_info.get("semester")

    if intent.get("semester") is not None and semester is not None and semester != intent["semester"]:
        return False

    if intent.get("exam_type") == "MID" and exam_type not in {"MID", "HONORS"} and "mid" not in combined:
        return False
    if intent.get("exam_type") == "SUPPLY" and exam_type != "SUPPLY" and "supply" not in combined:
        return False
    if intent.get("exam_type") == "REVALUATION" and exam_type != "REVALUATION" and "revaluation" not in combined:
        return False
    if intent.get("exam_type") == "REGULAR" and exam_type != "REGULAR" and "regular" not in combined:
        return False

    topic = intent.get("topic")
    if topic == "MOOCS" and "moocs" not in combined:
        return False
    if topic == "HONORS" and not any(word in combined for word in ["honors", "honor", "minor", "minors", "homi"]):
        return False
    if topic == "FSI" and "fsi" not in combined:
        return False
    if topic == "REVIEW" and "review" not in combined:
        return False

    year = intent.get("year")
    if year == 1 and not any(word in combined for word in ["iyear", "i year", "1 year", "1st year", "first year"]):
        return False
    if year == 2 and not any(word in combined for word in ["iiyear", "ii year", "2 year", "2nd year", "second year"]):
        return False
    if year == 3 and not any(word in combined for word in ["iiiyear", "iii year", "3 year", "3rd year", "third year"]):
        return False
    if year == 4 and not any(word in combined for word in ["ivyear", "iv year", "4 year", "4th year", "fourth year"]):
        return False

    if intent.get("mid_number") == 1 and not any(word in combined for word in ["mid one", "mid 1", "mid_one", "mid-one"]):
        return False
    if intent.get("mid_number") == 2 and not any(word in combined for word in ["mid two", "mid 2", "mid_two", "mid-two"]):
        return False

    batch = intent.get("batch")
    if batch and batch not in combined:
        return False
    
    admitted_batch = intent.get("admitted_batch")
    if admitted_batch:
        batch_variants = {
            admitted_batch,
            admitted_batch.replace("-", " - "),
            admitted_batch.replace("-", " to "),
        }
        if not any(variant in combined for variant in batch_variants):
            return False

    regulation = intent.get("regulation")
    if regulation == "AR23":
        if not any(token in combined for token in ["ar 23", "ar23", "r23", "regulation 2023", "autonomous regulation 2023"]):
            return False
    if regulation == "AR20":
        if not any(token in combined for token in ["ar 20", "ar20", "r20", "regulation 2020", "autonomous regulation 2020"]):
            return False
    if regulation == "AR20 REV 1.0":
        if not any(token in combined for token in ["ar 20 rev 1.0", "ar20 rev 1.0", "r20 rev 1.0", "2020 rev 1.0"]):
            return False


    if intent.get("document_type") == "TIMETABLE":
        if not any(word in combined for word in ["timetable", "schedule", "mid examination", "semester end examination", "review schedule"]):
            return False

    if intent.get("document_type") == "FEE" and "fee" not in combined:
        return False

    return True


# --------------------------------------------------
# RETRIEVE RELEVANT CHUNKS
# --------------------------------------------------

def lexical_score(query: str, candidate_text: str, *, title_chunk: bool = False) -> float:
    normalized_query = normalize_query(query)
    normalized_candidate = normalize_query(candidate_text)
    if not normalized_query or not normalized_candidate:
        return 0.0

    score = 0.0

    if normalized_query == normalized_candidate:
        score += 1.40
    elif normalized_query in normalized_candidate:
        score += 0.95

    query_tokens = set(tokenize_search_text(normalized_query))
    if query_tokens:
        token_hits = sum(
            1 for token in query_tokens
            if re.search(rf"\b{re.escape(token)}\b", normalized_candidate)
        )
        score += token_hits / len(query_tokens)

    if title_chunk:
        score += 0.15

    return score


def merge_ranked_results(*result_sets):
    merged = {}
    for result_set in result_sets:
        for text, score, doc_id in result_set or []:
            key = (doc_id, text)
            merged[key] = max(merged.get(key, float("-inf")), float(score or 0.0))

    merged_results = [
        (text, score, doc_id)
        for (doc_id, text), score in merged.items()
    ]
    return sorted(merged_results, key=lambda item: item[1], reverse=True)


def lexical_search_chunks(query: str, top_k: int = 30):
    chunks_by_doc = load_chunk_metadata()
    results = []

    for doc_id, chunks in (chunks_by_doc or {}).items():
        doc_info = get_doc_info(doc_id)
        base_text = combine_doc_text(doc_info)

        for chunk in chunks or []:
            chunk_text = chunk.get("text") if isinstance(chunk, dict) else ""
            if not chunk_text:
                continue

            score = lexical_score(
                query,
                f"{base_text} {chunk_text}",
                title_chunk=chunk_text.lower().startswith("[document title]"),
            )
            if score > 0.45:
                results.append((chunk_text, score, doc_id))

    results.sort(key=lambda item: item[1], reverse=True)
    return results[:top_k]

def retrieve_relevant_chunks(query: str, top_k: int = 20):
    try:
        normalized_query = normalize_query(query)
        query_embedding = get_embedding_model().encode([normalized_query]).tolist()[0]
    except Exception:
        return []

    intent = extract_query_intent(normalized_query)
    title_like_query = is_title_like_query(normalized_query)
    semester = intent.get("semester")
    exam_type = intent.get("exam_type")

    semantic_queries = []
    if title_like_query and semester is not None:
        semantic_queries.append(sqlite_store.query(query_embedding, top_k=max(top_k * 3, 40), semester=semester))
    elif semester is not None and exam_type is not None:
        semantic_queries.append(sqlite_store.query(query_embedding, top_k=max(top_k * 3, 40), semester=semester, doc_type=exam_type))
        semantic_queries.append(sqlite_store.query(query_embedding, top_k=max(top_k * 3, 40), semester=semester))
    elif semester is not None:
        semantic_queries.append(sqlite_store.query(query_embedding, top_k=max(top_k * 3, 40), semester=semester))

    semantic_queries.append(sqlite_store.query(query_embedding, top_k=max(top_k * 4, 60)))
    semantic_results = merge_ranked_results(*semantic_queries)
    lexical_results = lexical_search_chunks(normalized_query, top_k=max(top_k * 4, 60))
    results = merge_ranked_results(semantic_results, lexical_results)

    if not results:
        return []

    boosted_results = []
    for text, sim, doc_id in results:
        boost = 0.0
        text_lower = text.lower()

        doc_info = get_doc_info(doc_id)
        combined_text = combine_doc_text(doc_info, text_lower)
        normalized_chunk_text = normalize_query(text_lower)
        normalized_combined_text = normalize_query(combined_text)

        if normalized_query == normalized_chunk_text:
            boost += 0.60
        elif normalized_query in normalized_chunk_text:
            boost += 0.45
        elif normalized_query in normalized_combined_text:
            boost += 0.30

        if text_lower.startswith("[document title]"):
            boost += 0.12
        if text_lower.startswith("[important header info]"):
            boost += 0.08

        if "fsi" in normalized_query and "fsi" in combined_text:
            boost += 0.25
        if "moocs" in normalized_query and "moocs" in combined_text:
            boost += 0.25
        if "supply" in normalized_query and "supply" in combined_text:
            boost += 0.20
        if "revaluation" in normalized_query and "revaluation" in combined_text:
            boost += 0.20
        if "timetable" in normalized_query and "timetable" in combined_text:
            boost += 0.20
        if "schedule" in normalized_query and "schedule" in combined_text:
            boost += 0.20
        if "review" in normalized_query and "review" in combined_text:
            boost += 0.25
        if "fee" in normalized_query and "fee" in combined_text:
            boost += 0.20
        if "regular" in normalized_query and "regular" in combined_text:
            boost += 0.15
        if any(word in normalized_query for word in ["honor", "honors", "minor", "minors", "homi"]) and any(
            word in combined_text for word in ["honor", "honors", "minor", "minors", "homi"]
        ):
            boost += 0.30

        if (
            ("review" in normalized_query or "schedule" in normalized_query or "timetable" in normalized_query)
            and "fee" not in normalized_query
            and "fee" in combined_text
        ):
            boost -= 0.25

        boosted_results.append((text, sim + boost, doc_id))

    results = sorted(boosted_results, key=lambda x: x[1], reverse=True)

    strict_results = [
        (text, score, doc_id)
        for text, score, doc_id in results
        if document_matches_intent(doc_id, text, intent)
    ]

    strong_constraints = any([
        intent.get("year") is not None,
        intent.get("topic") is not None,
        intent.get("mid_number") is not None,
        intent.get("batch") is not None,
        intent.get("document_type") in {"TIMETABLE", "FEE"},
    ])

    if strict_results:
        results = strict_results
    elif strong_constraints:
        return []

    results = [r for r in results if r[1] > 0.32]
    return results[:top_k]
# --------------------------------------------------
# AUGMENT QUERY
# --------------------------------------------------
def augment_query(query: str, top_k: int = 8, min_similarity: float = 0.25, history: Optional[list] = None):
    """
    Augment a query with relevant knowledge base chunks.
    Returns (augmented_query_str, has_kb_content: bool, docs_info: list, low_confidence: bool)
    """
    if is_general_chat(query):
        return query, False, [], False

    retrieval_query = build_retrieval_query(query, history=history)
    relevant_chunks = retrieve_relevant_chunks(retrieval_query, top_k=top_k)

    if not relevant_chunks:
        return query, False, [], False

    filtered = [
        (chunk_text, sim, doc_id)
        for (chunk_text, sim, doc_id) in relevant_chunks
        if (sim or 0.0) >= min_similarity
    ]

    if not filtered:
        return query, False, [], False

    intent = extract_query_intent(normalize_query(retrieval_query))
    semester = intent.get("semester")

    if semester is not None:
        semester_filtered = []
        for chunk_text, sim, doc_id in filtered:
            doc_info = get_doc_info(doc_id)
            doc_semester = doc_info.get("semester")

            combined_doc_text = combine_doc_text(doc_info, chunk_text)
            if doc_semester == semester or has_explicit_semester_match(combined_doc_text, semester):
                semester_filtered.append((chunk_text, sim, doc_id))


        if semester_filtered:
            filtered = semester_filtered
        else:
            return query, False, [], True

    doc_map = {}
    for chunk_text, sim, doc_id in filtered:
        if not doc_id:
            continue
        doc_map.setdefault(doc_id, []).append((chunk_text, sim))

    if not doc_map:
        return query, False, [], False

    for doc_id in doc_map:
        doc_map[doc_id] = sorted(
            doc_map[doc_id],
            key=lambda x: x[1] or 0.0,
            reverse=True
        )[:4]

    doc_scores = {
        doc_id: max((score or 0.0) for _, score in chunks)
        for doc_id, chunks in doc_map.items()
    }

    best_score = max(doc_scores.values())
    if best_score < 0.42:
        return query, False, [], True

    primary_doc = max(doc_scores.items(), key=lambda x: x[1])[0]

    primary_chunks = sorted(
        doc_map[primary_doc],
        key=lambda x: x[1] or 0.0,
        reverse=True
    )[:8]

    primary_doc_info = get_doc_info(primary_doc)
    
    if not document_matches_intent(primary_doc, primary_chunks[0][0], intent):
        return query, False, [], True


    context_parts = []
    if primary_doc_info.get("title"):
        context_parts.append(f"DOCUMENT TITLE: {primary_doc_info['title']}")
    if primary_doc_info.get("semester") is not None:
        context_parts.append(f"SEMESTER: {primary_doc_info['semester']}")
    if primary_doc_info.get("exam_type"):
        context_parts.append(f"EXAM TYPE: {primary_doc_info['exam_type']}")

    context_parts.append(
        "\n\n".join(
            f"----- DOCUMENT CHUNK -----\n{chunk_text}"
            for chunk_text, _ in primary_chunks
        )
    )

    context = "\n\n".join(context_parts)

    best_chunk = max(primary_chunks, key=lambda x: x[1] or 0.0)
    snippet = (best_chunk[0][:400] + "...") if best_chunk[0] else None

    docs_info = [{
        "doc_id": primary_doc,
        "filename": primary_doc_info.get("filename"),
        "path": primary_doc_info.get("path"),
        "match_score": float(doc_scores.get(primary_doc)) if doc_scores.get(primary_doc) is not None else None,
        "snippet": snippet,
        "semester": primary_doc_info.get("semester"),
        "exam_type": primary_doc_info.get("exam_type"),
    }]

    augmented_query = (
        "You are an AI assistant for the university exam cell.\n\n"
        "Use the document content below to answer the student's question.\n"
        "Answer clearly using the information from the document.\n\n"
        f"STUDENT QUESTION:\n{query}\n\n"
        "DOCUMENT CONTENT:\n"
        + context
    )

    return augmented_query, True, docs_info, False


# --------------------------------------------------
# MAIN ENTRY FOR CHATBOT
# --------------------------------------------------
def answer_query(prompt: str, history: Optional[list] = None):
    """
    Main function used by chatbot.
    """
    history = history or []

    if is_general_chat(prompt):
        try:
            answer = generate_answer(prompt, "", history=history)
        except TypeError:
            answer = generate_answer(prompt, "")
        return answer, []

    augmented, has_kb, docs_info, low_confidence = augment_query(
        prompt,
        top_k=20,
        min_similarity=0.25,
        history=history
    )

    if not has_kb:
        intent = extract_query_intent(prompt)
        has_document_signal = any([
            intent.get("semester") is not None,
            intent.get("year") is not None,
            intent.get("exam_type") is not None,
            intent.get("document_type") is not None,
            intent.get("topic") is not None,
            intent.get("batch") is not None,
            intent.get("mid_number") is not None,
        ])

        short_chat = len(normalize_query(prompt).split()) <= 4

        if short_chat and not has_document_signal:
            try:
                answer = generate_answer(prompt, "", history=history)
            except TypeError:
                answer = generate_answer(prompt, "")
            return answer, []

        return (
            "I could not find a clearly matching uploaded exam cell document for this query. "
            "Please try mentioning the semester, year, exam type, batch, or a more complete document title.",
            []
        )




    try:
        answer = generate_answer(prompt, augmented, history=history)
    except TypeError:
        answer = generate_answer(prompt, augmented)
    except Exception:
        answer = "Unable to generate answer at this time."

    combined = f"**According to the Knowledge Base:**\n\n{answer}"
    return combined, docs_info
