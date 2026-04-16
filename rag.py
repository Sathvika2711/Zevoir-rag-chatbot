"""
=============================================================
  rag.py — THE RAG PIPELINE
  This is the brain of the chatbot.
=============================================================

WHAT THIS FILE DOES:
  1. Reads all your documents from the /documents folder
  2. Splits them into small chunks (pieces)
  3. Converts each chunk into a vector (list of numbers)
     that captures the MEANING of that chunk
  4. When a user asks a question:
     - Converts the question into a vector too
     - Finds the chunks whose vectors are most similar
     - Returns those chunks as context for Claude

WHY CHUNKS?
  We can't feed an entire document to Claude every time.
  So we split documents into small pieces and only feed
  the RELEVANT pieces for each question.

WHY VECTORS?
  Vectors let us find chunks by MEANING, not just keywords.
  "How much does a chatbot cost?" will find the pricing chunk
  even if the chunk uses words like "rate" and "fee" instead
  of "cost".

LIBRARIES USED:
  sentence-transformers → converts text to vectors (free, local)
  numpy                 → math for similarity calculation
"""

import os
import numpy as np
# SentenceTransformer converts text into vectors (embeddings)
# all-MiniLM-L6-v2 is a small, fast, free model that works well
from sentence_transformers import SentenceTransformer

# ── SETTINGS ──────────────────────────────────────────────────
DOCUMENTS_FOLDER = "documents"   # folder where your .txt files live
CHUNK_SIZE        = 300          # words per chunk
CHUNK_OVERLAP     = 50           # words shared between adjacent chunks
TOP_K             = 3            # how many chunks to retrieve per query


# ── LOAD THE EMBEDDING MODEL ───────────────────────────────────
# This downloads automatically on first run (~90MB)
# After first run it's cached locally — no re-download needed
print("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model loaded.")


# ── FUNCTION: SPLIT TEXT INTO CHUNKS ──────────────────────────
def split_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Splits a long text into smaller overlapping chunks.

    Why overlap?
    If an important sentence is at the end of chunk 1 and
    the beginning of chunk 2, overlap ensures it appears
    fully in at least one chunk.

    text:       the full document text
    chunk_size: how many words per chunk
    overlap:    how many words to repeat between chunks
    Returns:    list of text chunk strings
    """
    words  = text.split()   # split into individual words
    chunks = []
    i = 0

    while i < len(words):
        # Take chunk_size words starting at position i
        chunk_words = words[i : i + chunk_size]
        chunk_text  = " ".join(chunk_words)
        chunks.append(chunk_text)
        # Move forward by (chunk_size - overlap) so chunks overlap
        i += max(1, chunk_size - overlap)

    return chunks


# ── FUNCTION: LOAD AND INDEX ALL DOCUMENTS ────────────────────
def load_documents():
    """
    Reads all .txt files in the documents folder,
    splits them into chunks, and embeds each chunk.

    Returns a list of dicts:
    [
      {
        "text":     "chunk text here...",
        "source":   "services.txt",
        "embedding": [0.23, -0.45, 0.78, ...]  (384 numbers)
      },
      ...
    ]
    """
    all_chunks = []

    # Loop through every file in the documents folder
    for filename in os.listdir(DOCUMENTS_FOLDER):
        if not filename.endswith(".txt"):
            continue   # skip non-text files

        filepath = os.path.join(DOCUMENTS_FOLDER, filename)

        # Read the file
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # Split into chunks
        chunks = split_into_chunks(text)

        # Add each chunk with its source filename
        for chunk in chunks:
            all_chunks.append({
                "text":   chunk,
                "source": filename,
            })

    print(f"Loaded {len(all_chunks)} chunks from {DOCUMENTS_FOLDER}/")

    # Embed all chunks at once (batch processing = faster)
    texts = [c["text"] for c in all_chunks]
    print("Embedding all chunks...")
    embeddings = embedding_model.encode(texts, show_progress_bar=False)

    # Add embedding to each chunk dict
    for i, chunk in enumerate(all_chunks):
        chunk["embedding"] = embeddings[i]

    print(f"Indexed {len(all_chunks)} chunks successfully.")
    return all_chunks


# ── FUNCTION: COSINE SIMILARITY ───────────────────────────────
def cosine_similarity(vec_a, vec_b):
    """
    Measures how similar two vectors are.
    Result: 1.0 = identical meaning, 0.0 = completely different

    This is how we find the most relevant chunks for a query.
    The question vector is compared to every chunk vector.
    The chunks with the highest similarity score are returned.
    """
    # dot product divided by product of magnitudes
    dot     = np.dot(vec_a, vec_b)
    norm_a  = np.linalg.norm(vec_a)
    norm_b  = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── FUNCTION: RETRIEVE RELEVANT CHUNKS ────────────────────────
def retrieve(query, chunks, top_k=TOP_K):
    """
    Given a user's question and all indexed chunks,
    returns the top_k most relevant chunks.

    query:  the user's question (string)
    chunks: all indexed chunks with embeddings
    top_k:  how many chunks to return
    Returns: list of the most relevant chunk dicts
    """
    # Step 1: Convert the question to a vector
    query_embedding = embedding_model.encode([query])[0]

    # Step 2: Compare question vector to every chunk vector
    scored = []
    for chunk in chunks:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        scored.append((score, chunk))

    # Step 3: Sort by similarity score (highest first)
    scored.sort(key=lambda x: x[0], reverse=True)

    # Step 4: Return top_k most relevant chunks
    top_chunks = [chunk for score, chunk in scored[:top_k]]
    return top_chunks


# ── GLOBAL: INDEX DOCUMENTS ON STARTUP ────────────────────────
# This runs once when the server starts.
# All chunks are loaded and embedded into memory.
# Future queries just search this in-memory index — very fast.
INDEXED_CHUNKS = load_documents()
