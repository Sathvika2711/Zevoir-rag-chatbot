"""
tests/test_rag.py — Unit tests for rag.py pure functions
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

# Mock SentenceTransformer before importing rag.py.
# The mock's encode() returns one fake 3-dim embedding per input text
# so load_documents() can run without crashing.
mock_model = MagicMock()
mock_model.encode.side_effect = lambda texts, **kwargs: np.array(
    [[0.1, 0.2, 0.3]] * (len(texts) if isinstance(texts, list) else 1)
)

with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
    from rag import split_into_chunks, cosine_similarity


# ── Tests for split_into_chunks() ─────────────────────────────

class TestSplitIntoChunks:

    def test_short_text_returns_one_chunk(self):
        """A short text should return exactly one chunk"""
        chunks = split_into_chunks("This is a short sentence.", chunk_size=50, overlap=10)
        assert len(chunks) == 1

    def test_long_text_returns_multiple_chunks(self):
        """A text longer than chunk_size words should be split"""
        text = " ".join(["word"] * 200)
        chunks = split_into_chunks(text, chunk_size=50, overlap=10)
        assert len(chunks) > 1

    def test_chunk_size_is_respected(self):
        """Each chunk should not exceed chunk_size words"""
        text = " ".join(["word"] * 300)
        chunks = split_into_chunks(text, chunk_size=50, overlap=0)
        for chunk in chunks:
            assert len(chunk.split()) <= 50

    def test_empty_text_returns_empty_list(self):
        """Empty text should return empty list"""
        assert split_into_chunks("", chunk_size=50, overlap=10) == []

    def test_overlap_means_content_is_shared(self):
        """With overlap, end of chunk 0 should appear at start of chunk 1"""
        words = [f"word{i}" for i in range(20)]
        chunks = split_into_chunks(" ".join(words), chunk_size=10, overlap=5)
        if len(chunks) >= 2:
            assert chunks[0].split()[-5:] == chunks[1].split()[:5]

    def test_returns_list_of_strings(self):
        """Should always return a list of strings"""
        chunks = split_into_chunks("Hello world this is a test.")
        assert isinstance(chunks, list)
        assert all(isinstance(c, str) for c in chunks)


# ── Tests for cosine_similarity() ─────────────────────────────

class TestCosineSimilarity:

    def test_identical_vectors_return_one(self):
        vec = np.array([1.0, 2.0, 3.0])
        assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-6

    def test_opposite_vectors_return_minus_one(self):
        assert abs(cosine_similarity(
            np.array([1.0, 0.0, 0.0]),
            np.array([-1.0, 0.0, 0.0])
        ) - (-1.0)) < 1e-6

    def test_orthogonal_vectors_return_zero(self):
        assert abs(cosine_similarity(
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0])
        )) < 1e-6

    def test_zero_vector_returns_zero(self):
        """Should not crash with a zero vector — returns 0.0"""
        assert cosine_similarity(np.array([0.0, 0.0, 0.0]), np.array([1.0, 2.0, 3.0])) == 0.0

    def test_result_is_between_minus_one_and_one(self):
        result = cosine_similarity(np.array([0.5, 0.8, -0.3]), np.array([-0.1, 0.6, 0.9]))
        assert -1.0 <= result <= 1.0

    def test_similar_vectors_score_higher_than_dissimilar(self):
        query      = np.array([1.0, 1.0, 0.0])
        similar    = np.array([0.9, 0.9, 0.1])
        dissimilar = np.array([0.0, 0.0, 1.0])
        assert cosine_similarity(query, similar) > cosine_similarity(query, dissimilar)
