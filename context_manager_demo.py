"""
context_manager_demo.py — Context Manager Example for Zevoir

WHAT IS A CONTEXT MANAGER?
  A context manager is a Python object that handles setup and
  teardown automatically using the 'with' statement.

  You already use one in your code:
      with open(filepath, "r") as f:
          text = f.read()

  The 'with' statement guarantees the file is closed after
  the block — even if an error occurs inside it.

THIS FILE SHOWS:
  1. How to build your OWN context manager using __enter__ / __exit__
  2. A practical example: wrapping the document loading from rag.py
     so it logs timing and handles errors cleanly

WHY THIS MATTERS FOR OPTIVER:
  Context managers are used constantly in production code for:
    - Database connections (open → use → close)
    - File handling (open → read/write → close)
    - API sessions (create → use → teardown)
    - Locks and semaphores in async/concurrent code
"""

import time
import os


# ──────────────────────────────────────────────────────────────
# APPROACH 1: Class-based context manager
# Uses __enter__ and __exit__ magic methods
# ──────────────────────────────────────────────────────────────

class DocumentLoader:
    """
    A context manager that loads documents from a folder.

    Usage:
        with DocumentLoader("documents/") as loader:
            chunks = loader.get_chunks()

    On enter: opens the folder, records start time
    On exit:  logs how many files were loaded and how long it took
              also handles errors gracefully
    """

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.files_loaded = 0
        self.start_time = None

    def __enter__(self):
        """
        Called when entering the 'with' block.
        Sets up timing and validates the folder exists.
        Returns self so we can use it inside the with block.
        """
        if not os.path.exists(self.folder_path):
            raise FileNotFoundError(f"Documents folder not found: {self.folder_path}")

        self.start_time = time.time()
        print(f"[DocumentLoader] Opening folder: {self.folder_path}")
        return self   # this becomes the 'as loader' variable

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called when leaving the 'with' block — always runs.
        Even if an exception occurred inside the block.

        exc_type:  the exception class (None if no error)
        exc_val:   the exception message (None if no error)
        exc_tb:    the traceback (None if no error)

        Return True  → suppress the exception (swallow it)
        Return False → let the exception propagate (re-raise it)
        """
        elapsed = time.time() - self.start_time

        if exc_type is not None:
            # An error occurred inside the with block
            print(f"[DocumentLoader] ERROR during loading: {exc_val}")
            print(f"[DocumentLoader] Elapsed before error: {elapsed:.3f}s")
            return False  # re-raise the exception — don't hide errors

        # No error — log the success
        print(f"[DocumentLoader] Loaded {self.files_loaded} files in {elapsed:.3f}s")
        return False

    def get_chunks(self, chunk_size: int = 300) -> list:
        """Read all .txt files and split into word chunks"""
        all_chunks = []

        for filename in os.listdir(self.folder_path):
            if not filename.endswith(".txt"):
                continue

            filepath = os.path.join(self.folder_path, filename)

            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()

            # Simple word-based chunking (same logic as rag.py)
            words = text.split()
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                all_chunks.append({"text": chunk, "source": filename})

            self.files_loaded += 1

        return all_chunks


# ──────────────────────────────────────────────────────────────
# APPROACH 2: Generator-based context manager using @contextmanager
# Simpler to write for straightforward cases
# ──────────────────────────────────────────────────────────────

from contextlib import contextmanager

@contextmanager
def timed_operation(operation_name: str):
    """
    A simple context manager that times any block of code.

    Usage:
        with timed_operation("embedding documents"):
            embeddings = model.encode(texts)

    Everything before 'yield' = setup (__enter__)
    Everything after  'yield' = teardown (__exit__)
    """
    print(f"[Timer] Starting: {operation_name}")
    start = time.time()

    try:
        yield   # control passes to the 'with' block here
    except Exception as e:
        print(f"[Timer] {operation_name} failed: {e}")
        raise   # re-raise so the error isn't hidden
    finally:
        # 'finally' always runs — same as __exit__
        elapsed = time.time() - start
        print(f"[Timer] {operation_name} completed in {elapsed:.3f}s")


# ──────────────────────────────────────────────────────────────
# DEMO — run both context managers
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  DEMO 1: Class-based DocumentLoader context manager")
    print("=" * 55)

    # Using the DocumentLoader — note 'documents/' is the Zevoir folder
    try:
        with DocumentLoader("documents") as loader:
            chunks = loader.get_chunks()
            print(f"  Got {len(chunks)} total chunks")
    except FileNotFoundError as e:
        print(f"  (Run from inside zevoir_rag/ folder): {e}")

    print()
    print("=" * 55)
    print("  DEMO 2: Generator-based timed_operation context manager")
    print("=" * 55)

    with timed_operation("simulated embedding"):
        time.sleep(0.1)   # pretend we're doing work
        print("  Embedding complete.")

    print()
    print("=" * 55)
    print("  KEY TAKEAWAY")
    print("=" * 55)
    print("  Both context managers guarantee cleanup happens")
    print("  even if an exception is raised inside the block.")
    print()
    print("  In an interview: 'I used context managers to handle")
    print("  document loading in my RAG chatbot — they guaranteed")
    print("  timing and error logging ran even on failures.'")
