import re


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 60):
    if not text or not text.strip():
        return []

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Split text into meaningful segments:
    # 1. punctuation-based sentence boundaries
    # 2. line boundaries for OCR/timetable/circular content
    raw_segments = re.split(r'(?<=[.!?])\s+|\n+|(?<=:)\s+', text)
    sentences = [segment.strip() for segment in raw_segments if segment and segment.strip()]

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        words = sentence.split()
        word_count = len(words)

        if word_count == 0:
            continue

        # If single segment is too large, flush current chunk first
        if word_count > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

            for i in range(0, word_count, chunk_size):
                long_chunk_words = words[i:i + chunk_size]
                if long_chunk_words:
                    chunks.append(" ".join(long_chunk_words))
            continue

        # Add segment if it fits
        if current_length + word_count <= chunk_size:
            current_chunk.extend(words)
            current_length += word_count
        else:
            # Save current chunk
            if current_chunk:
                chunks.append(" ".join(current_chunk))

            # Apply overlap
            overlap_words = current_chunk[-overlap:] if overlap and current_chunk else []
            current_chunk = overlap_words + words
            current_length = len(current_chunk)

    # Final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
