from pathlib import Path
import pdfplumber
import docx
import re

from backend.ingestion.chunker import chunk_text
from backend.ingestion.ocr import apply_ocr
from backend.retrieval.search import store_document


def basic_clean(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_reversed_ocr_line(line: str) -> bool:
    lower_line = line.lower()

    reversed_markers = [
        "yadirf",      # friday
        "yadsenw",     # wednesday
        "yadsruht",    # thursday
        "yadnom",      # monday
        "noitanimaxe", # examination
        "gnireenigne", # engineering
        "elbatemit",   # timetable
        "etaluc",      # calculus (partial bad OCR pattern)
    ]

    hits = sum(marker in lower_line for marker in reversed_markers)
    return hits >= 1 and len(line.split()) >= 4


def fix_reversed_ocr_line(line: str) -> str:
    if is_reversed_ocr_line(line):
        return line[::-1]
    return line



def normalize_ocr_text(text: str) -> str:
    """
    Clean OCR text before chunking and vector storage.
    Keeps line structure so title/header extraction still works.
    """

    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = re.sub(r"[^\x00-\x7F]+", " ", line)
        line = fix_reversed_ocr_line(line)


        # Fix spaced letters like: A c a d e m i c -> Academic
        line = re.sub(
            r"(?:(?<=\s)|^)([A-Za-z])(?:\s+([A-Za-z])){2,}",
            lambda m: m.group(0).replace(" ", ""),
            line,
        )

        # Fix merged lowercase-uppercase words
        line = re.sub(r"([a-z])([A-Z])", r"\1 \2", line)

        # Fix letter-number joins
        line = re.sub(r"([A-Za-z])(\d)", r"\1 \2", line)
        line = re.sub(r"(\d)([A-Za-z])", r"\1 \2", line)

        # Fix spaced numbers in dates
        line = re.sub(r"(\d)\s+(?=\d)", r"\1", line)

        # Fix dotted abbreviations
        line = re.sub(r"\s*\.\s*", ".", line)

        # Fix spaces around brackets
        line = re.sub(r"\(\s+", "(", line)
        line = re.sub(r"\s+\)", ")", line)

        # Fix spaces before punctuation
        line = re.sub(r"\s+([.,:;])", r"\1", line)

        # Remove strange OCR symbols
        line = re.sub(r'[“”"\'`]', " ", line)

        # Fix subject names broken by OCR
        line = re.sub(r"Engi\s*neer\s*ing", "Engineering", line, flags=re.IGNORECASE)

        # fix common OCR mistakes
        line = re.sub(r"\bfsl review\b", "fsi review", line, flags=re.IGNORECASE)
        line = re.sub(r"\bfsl schedule\b", "fsi schedule", line, flags=re.IGNORECASE)

        # remove broken OCR noise but keep useful punctuation and page markers
        line = re.sub(r"[^a-zA-Z0-9.,:;()\[\] /\-&|]", " ", line)

        # normalize spaces inside line
        line = re.sub(r"[ \t]+", " ", line).strip()

        if line:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = text.lower()
    
    
    # Common OCR normalization fixes
    text = re.sub(r"\bil year\b", "ii year", text)
    text = re.sub(r"\bil examination\b", "ii examination", text)
    text = re.sub(r"\bil semester\b", "ii semester", text)

    text = re.sub(r"\bvill semester\b", "viii semester", text)
    text = re.sub(r"\bvi i semester\b", "vii semester", text)
    text = re.sub(r"\bsem ester\b", "semester", text)
    text = re.sub(r"\bexaminat ion\b", "examination", text)
    text = re.sub(r"\bsch edule\b", "schedule", text)
    text = re.sub(r"\bautono mous\b", "autonomous", text)

    text = re.sub(r"\bb\.t ech\b", "b.tech", text)
    text = re.sub(r"\bb\. tech\b", "b.tech", text)
    text = re.sub(r"\btech\s*-\s*semester\b", "b.tech. i semester", text)

    text = re.sub(r"\bmid\s*-\s*il\b", "mid - ii", text)
    text = re.sub(r"\bmid\s*-\s*examination\s+b\.tech\.\s*vill semester\b", "mid - examination b.tech. viii semester", text)
    text = re.sub(r"\bdepartment mid\s*-\s*il examination\b", "department mid - ii examination", text)

    text = re.sub(r"\bmoocs examinat ion sch edule\b", "moocs examination schedule", text)
    text = re.sub(r"\bmoocs examination schedule for b\.tech\.vi i semester\b", "moocs examination schedule for b.tech. vii semester", text)

    text = re.sub(r"\bfsi review schedule for b\.tech\.semester vii\b", "fsi review schedule for b.tech. semester vii", text)

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
        text = re.sub(pattern, replacement, text)


    # remove repeated random letters
    text = re.sub(r"\b[a-z]\s[a-z]\s[a-z]\b", " ", text)

    # preserve line structure but clean repeated blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def compute_semester(year, sem_in_year):
    if year is None or sem_in_year is None:
        return None
    return (year - 1) * 2 + sem_in_year

def build_filename_title(filename: str) -> str:
    stem = Path(filename).stem
    title = stem.replace("_", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title.lower()


def is_generic_title_candidate(title: str) -> bool:
    clean_title = (title or "").strip().lower()
    if not clean_title:
        return True

    if any(
        marker in clean_title
        for marker in [
            "office of the controller of examinations",
            "controller of examinations",
            "copyto",
        ]
    ):
        return True

    if re.fullmatch(r"[\d\s:/().-]+", clean_title):
        return True

    words = re.findall(r"[a-z0-9]+", clean_title)
    if len(words) < 4:
        return True

    if len(set(words)) <= 2:
        return True

    return False

def looks_like_valid_title(text: str) -> bool:
    lower = (text or "").strip().lower()
    if not lower:
        return False

    preferred_keywords = [
        "examination",
        "timetable",
        "schedule",
        "revaluation",
        "supplementary",
        "supply",
        "mid",
        "semester",
        "fee",
        "review",
        "fsi",
        "circular",
        "regular",
    ]

    if "office of the controller of examinations" == lower:
        return False

    if not any(keyword in lower for keyword in preferred_keywords):
        return False

    words = re.findall(r"[a-z0-9.]+", lower)
    if len(words) < 4:
        return False

    short_words = sum(1 for word in words if len(word) <= 2)
    if words and short_words / len(words) > 0.35:
        return False

    if len(re.findall(r"[a-z]", lower)) < 12:
        return False

    return True


def extract_metadata_from_filename(filename: str) -> dict:
    name = re.sub(r"[^A-Z0-9]+", " ", Path(filename).stem.upper()).strip()

    year = None
    for pattern, value in [
        (r"\bIVYEAR\b", 4),
        (r"\bIIIYEAR\b", 3),
        (r"\bIIYEAR\b", 2),
        (r"\bIYEAR\b", 1),
    ]:
        if re.search(pattern, name):
            year = value
            break

    sem_in_year = None
    for pattern, value in [
        (r"\bIISEM\b", 2),
        (r"\bISEM\b", 1),
    ]:
        if re.search(pattern, name):
            sem_in_year = value
            break

    semester = compute_semester(year, sem_in_year)

    if "MID" in name:
        exam_type = "MID"
    elif "SUPPLY" in name or "SUPPLEMENTARY" in name:
        exam_type = "SUPPLY"
    elif "REVALUATION" in name:
        exam_type = "REVALUATION"
    elif "REGULAR" in name:
        exam_type = "REGULAR"
    elif "TIMETABLE" in name or "TIME TABLE" in name:
        exam_type = "TIMETABLE"
    elif "FEE" in name:
        exam_type = "FEE"
    elif "HOMI" in name or "HONORS" in name or "MINOR" in name:
        exam_type = "HONORS"
    else:
        exam_type = "GENERAL"

    return {
        "year": year,
        "semester": semester,
        "exam_type": exam_type,
    }

def extract_metadata_from_text(text: str) -> dict:
    t = text.lower()

    semester = None

    numeric_match = re.search(r"\b([1-8])(st|nd|rd|th)?\s*(sem|semester)\b", t)
    if numeric_match:
        semester = int(numeric_match.group(1))
    else:
        reverse_match = re.search(r"\b(sem|semester)\s*([1-8])\b", t)
        if reverse_match:
            semester = int(reverse_match.group(2))
        elif "8th semester" in t:
            semester = 8
        elif "7th semester" in t:
            semester = 7
        elif "6th semester" in t:
            semester = 6
        elif "5th semester" in t:
            semester = 5
        elif "4th semester" in t:
            semester = 4
        elif "3rd semester" in t:
            semester = 3
        elif "2nd semester" in t:
            semester = 2
        elif "1st semester" in t:
            semester = 1

    exam_type = classify_document(text).upper()

    return {
        "year": None,
        "semester": semester,
        "exam_type": exam_type,
    }


def extract_text_from_pdf(pdf_path: Path) -> str:
    def clean_cell(cell):
        if cell is None:
            return ""
        return re.sub(r"\s+", " ", str(cell)).strip()

    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_parts = [f"[PAGE {page.page_number}]"]

            page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if page_text:
                page_parts.append(page_text)

            tables = []
            table_settings_candidates = [
                {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                    "intersection_tolerance": 3,
                },
                {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                    "intersection_tolerance": 3,
                },
            ]

            for settings in table_settings_candidates:
                try:
                    extracted = page.extract_tables(settings)
                    if extracted:
                        tables = extracted
                        break
                except Exception:
                    continue

            for table in tables or []:
                formatted_rows = []

                for row in table:
                    if not row:
                        continue

                    cells = [clean_cell(cell) for cell in row]
                    cells = [cell for cell in cells if cell]

                    if len(cells) >= 2:
                        formatted_rows.append(" | ".join(cells))
                    elif len(cells) == 1:
                        formatted_rows.append(cells[0])

                if formatted_rows:
                    page_parts.append("[TABLE]")
                    page_parts.extend(formatted_rows)

            text_parts.append("\n".join(page_parts))

    return "\n\n".join(text_parts)



def extract_text_from_docx(docx_path: Path) -> str:
    def clean_cell(cell_text: str) -> str:
        return re.sub(r"\s+", " ", (cell_text or "").strip())

    doc = docx.Document(docx_path)
    parts = []

    # Normal paragraphs
    for paragraph in doc.paragraphs:
        text = re.sub(r"\s+", " ", paragraph.text).strip()
        if text:
            parts.append(text)

    # Tables
    for table in doc.tables:
        table_rows = []

        for row in table.rows:
            cells = [clean_cell(cell.text) for cell in row.cells]
            cells = [cell for cell in cells if cell]

            row_text = " | ".join(cells).lower()

            if any(skip_text in row_text for skip_text in [
                "controller of examinations",
                "principal",
                "copy to",
                "notice board",
                "accounts",
                "website",
                "file",
            ]):
                continue

            if len(cells) >= 2:
                table_rows.append(" | ".join(cells))
            elif len(cells) == 1:
                table_rows.append(cells[0])

        if table_rows:
            parts.append("[TABLE]")
            parts.extend(table_rows)

    return "\n".join(parts)


def validate_exam_cell_content(text: str):
    if not text or not isinstance(text, str):
        return False, "No readable text found in document"

    t = text.lower()
    t = re.sub(r"[^a-z0-9\. ]+", " ", t)

    authority_markers = [
        "controller of examinations",
        "nadimpalli",
        "satyanarayana",
        "raju",
    ]

    examcontext_markers = [
        "exam",
        "examination",
        "semester",
        "b.tech",
        "mid",
        "revaluation",
        "supplementary",
        "supply",
        "timetable",
        "time table",
        "academic year",
        "autonomous",
        "controller",
        "schedule",
        "notification",
        "fee",
    ]

    for marker in authority_markers:
        if marker in t:
            return True, f"Validation passed: found '{marker}'"

    for marker in examcontext_markers:
        if marker in t:
            return True, f"Validation passed: found '{marker}'"

    return False, "Validation failed: no examcell authority keywords found"


def classify_document(text: str):
    t = text.lower()

    if "revaluation" in t:
        return "REVALUATION"
    if "time table" in t or "timetable" in t:
        return "TIMETABLE"
    if "fee" in t:
        return "FEE"
    if "supplementary" in t or "supply" in t:
        return "SUPPLY"
    if "regular" in t:
        return "REGULAR"
    if "honors" in t or "minor" in t or "homi" in t:
        return "HONORS"
    if "mid" in t:
        return "MID"
    return "GENERAL"


def extract_title_line(text: str) -> str:
    lines = []

    for raw_line in text.splitlines()[:30]:
        clean_line = re.sub(r"\s+", " ", raw_line.strip())
        lower_line = clean_line.lower()

        if not clean_line:
            continue
        if lower_line.startswith("[page"):
            continue
        if re.search(r"\b(estd|established|id)\.?\s*\d{4}\b", lower_line):
            continue

        lines.append(clean_line)

    for i in range(len(lines)):
        for window in (3, 2, 1):
            candidate = " ".join(lines[i:i + window]).strip()
            candidate = re.sub(r"\s+", " ", candidate)

            if looks_like_valid_title(candidate):
                return candidate

    return ""


def process_document(
    original_path: Path,
    processed_dir: Path,
    dpi: int = 300,
    force_ocr: bool = False,
):
    """
    Main ingestion pipeline:
    - OCR if required
    - Text extraction
    - Chunking
    - Store in vector DB
    """

    processed_dir.mkdir(parents=True, exist_ok=True)

    ext = original_path.suffix.lower()
    processed_path = processed_dir / original_path.name

    if ext == ".pdf" and force_ocr:
        apply_ocr(original_path, processed_path, dpi=dpi)

    if not processed_path.exists():
        import shutil
        shutil.copy2(original_path, processed_path)

    if ext == ".pdf":
        text = extract_text_from_pdf(processed_path)
    elif ext == ".docx":
        text = extract_text_from_docx(processed_path)
    elif ext == ".doc":
        raise RuntimeError(".doc files are not supported. Please convert to .docx.")
    else:
        raise ValueError("Unsupported file type")

    if ext == ".pdf" and (not text or len(text.strip()) < 100):
        from backend.ingestion.ocr import ocr_pdf_to_text_tesseract

        ttxt = ocr_pdf_to_text_tesseract(processed_path, dpi=dpi)
        if ttxt:
            text = ttxt

    text = normalize_ocr_text(text)
    text = re.sub(r"[ \t]+", " ", text)

    if len(text.split()) < 50:
        print("⚠️ Poor text quality detected")

    header_keywords = [
        "controller",
        "examinations",
        "semester",
        "b.tech",
        "mid",
        "timetable",
        "time table",
        "academic year",
        "autonomous",
        "fee",
        "revaluation",
        "review",
        "schedule",
        "fsi",
        "supply",
        "supplementary",
        "circular",
    ]

    header_lines = []
    for line in text.splitlines()[:25]:
        clean_line = re.sub(r"\s+", " ", line.strip())
        lower_line = clean_line.lower()

        if not clean_line:
            continue
        if lower_line.startswith("[page"):
            continue
        if lower_line.startswith("[table]"):
            continue
        if "approved by aicte" in lower_line:
            continue
        if "affiliated to" in lower_line:
            continue
        if "recognized under section" in lower_line:
            continue
        if "accredited by naac" in lower_line:
            continue
        if lower_line.startswith("copy to"):
            continue
        if "notice board" in lower_line:
            continue
        if "accounts" in lower_line:
            continue
        if "website" in lower_line:
            continue
        if "principal" in lower_line:
            continue
        if lower_line.strip() in {
            "office of controller of examination",
            "office of the controller of examinations",
            "controller of examinations",
        }:
            continue

        if any(keyword in lower_line for keyword in header_keywords):
            header_lines.append(clean_line)

        if len(header_lines) >= 3:
            break

    forced_header_chunk = ""
    if header_lines:
        forced_header_chunk = " ".join(header_lines[:3])

    print("========== TEXT BEFORE VALIDATION ==========")
    print(text[:20000])
    print("===========================================")

    is_valid, reason = validate_exam_cell_content(text)
    if not is_valid:
        print(f"[DOCUMENT REJECTED] {reason}")
        return None

    title_line = extract_title_line(text)
    if is_generic_title_candidate(title_line):
        title_line = build_filename_title(original_path.name)

    chunks = []

    if title_line:
        chunks.append(f"[DOCUMENT TITLE] {title_line}")

    if forced_header_chunk:
        chunks.append(f"[IMPORTANT HEADER INFO] {forced_header_chunk}")

    body_lines = []

    for line in text.splitlines():
        clean_line = re.sub(r"\s+", " ", line.strip())
        lower_line = clean_line.lower()

        if not clean_line:
            continue
        if lower_line.startswith("[page"):
            continue
        if lower_line.startswith("copy to"):
            continue
        if "notice board" in lower_line:
            continue
        if "accounts" in lower_line:
            continue
        if "website" in lower_line:
            continue
        if lower_line == "file":
            continue
        if "controller of examinations | principal" in lower_line:
            continue
        if "principal" in lower_line and "controller of examinations" in lower_line:
            continue

        body_lines.append(clean_line)

    body_text = "\n".join(body_lines)

    if title_line:
        body_text = body_text.replace(title_line, "", 1)

    if forced_header_chunk:
        body_text = body_text.replace(forced_header_chunk, "", 1)

    body_text = re.sub(r"\n{3,}", "\n\n", body_text)
    body_text = body_text.strip()

    normal_chunks = chunk_text(body_text)
    chunks.extend(normal_chunks)

    if not normal_chunks and not title_line and not forced_header_chunk:
        raise RuntimeError(
            "No text was extracted from the document. "
            "If this is a scanned PDF try enabling 'Force OCR' or convert the file to DOCX."
        )

    doc_tags = extract_metadata_from_filename(original_path.name)

    if doc_tags.get("semester") is None or doc_tags.get("exam_type") in ["GENERAL", None]:
        text_meta = extract_metadata_from_text(text)

        if doc_tags.get("semester") is None:
            doc_tags["semester"] = text_meta.get("semester")

        if doc_tags.get("year") is None:
            doc_tags["year"] = text_meta.get("year")

        if doc_tags.get("exam_type") in ["GENERAL", None] and text_meta.get("exam_type"):
            doc_tags["exam_type"] = text_meta.get("exam_type")

    doc_tags["title"] = title_line
    doc_tags["keywords"] = title_line.lower().split() if title_line else []

    print("📘 DOCUMENT METADATA:", doc_tags)
    print("📄 CHUNK COUNT:", len(chunks))
    print("🔹 SAMPLE CHUNKS:", chunks[:2])

    if doc_tags.get("semester") is None:
        print("⚠️ WARNING: Semester could not be detected")

    if doc_tags.get("exam_type") == "GENERAL":
        print("⚠️ WARNING: Exam type unclear")

    doc_id = store_document(
        chunks=chunks,
        source_path=str(processed_path),
        doc_tags=doc_tags,
    )

    return doc_id
