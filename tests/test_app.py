"""
tests/test_app.py — Unit tests for app.py

We test:
  1. check_conversation_flow() — pure logic, no mocking needed
  2. /chat endpoint — we mock Claude + RAG so no API key needed

WHY MOCKING?
  The /chat endpoint calls Claude API and the RAG pipeline.
  In unit tests we don't want to make real API calls because:
    - It costs money
    - It requires a valid API key
    - It's slow
    - Tests should be deterministic (same result every time)

  So we use unittest.mock to replace those calls with fake ones
  that return predictable values.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import json
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────────────────────
# Tests for check_conversation_flow()
# ──────────────────────────────────────────────────────────────

class TestConversationFlow:

    def setup_method(self):
        """Import check_conversation_flow before each test"""
        # We patch the rag import so the embedding model doesn't load
        with patch.dict("sys.modules", {
            "rag": MagicMock(retrieve=MagicMock(), INDEXED_CHUNKS=[]),
            "anthropic": MagicMock()
        }):
            from app import check_conversation_flow
            self.check = check_conversation_flow

    def test_hello_triggers_greeting(self):
        """'hello' should match the greeting flow"""
        result = self.check("hello")
        assert result is not None
        assert "Welcome" in result or "Hello" in result

    def test_bye_triggers_farewell(self):
        """'bye' should match the farewell flow"""
        result = self.check("bye")
        assert result is not None
        assert "Thank you" in result or "wonderful" in result

    def test_thanks_triggers_acknowledgement(self):
        """'thanks' should match the thank you flow"""
        result = self.check("thanks")
        assert result is not None
        assert "welcome" in result.lower()

    def test_forgot_password_triggers_support(self):
        """'forgot password' should match the login support flow"""
        result = self.check("forgot password")
        assert result is not None
        assert "reset" in result.lower() or "password" in result.lower()

    def test_unknown_message_returns_none(self):
        """A question about services should return None (goes to RAG)"""
        result = self.check("what are your pricing plans?")
        assert result is None

    def test_case_insensitive_matching(self):
        """Flow matching should work regardless of capitalisation"""
        result_lower = self.check("hello")
        result_upper = self.check("HELLO")
        result_mixed = self.check("Hello")
        # All three should either all match or all not match
        assert (result_lower is None) == (result_upper is None) == (result_mixed is None)


# ──────────────────────────────────────────────────────────────
# Tests for /chat endpoint
# ──────────────────────────────────────────────────────────────

class TestChatEndpoint:

    @pytest.fixture(autouse=True)
    def setup_app(self):
        """
        Set up the Flask test client before each test.
        We mock out rag and anthropic so nothing real is called.
        """
        mock_rag = MagicMock()
        mock_rag.retrieve.return_value = [{"text": "Test chunk", "source": "faq.txt"}]
        mock_rag.INDEXED_CHUNKS = []

        mock_anthropic = MagicMock()

        with patch.dict("sys.modules", {"rag": mock_rag, "anthropic": mock_anthropic}):
            import importlib
            import app as app_module
            importlib.reload(app_module)
            app_module.app.config["TESTING"] = True
            self.client = app_module.app.test_client()
            self.app_module = app_module

    def test_chat_returns_200(self):
        """/chat should return HTTP 200 for a valid message"""
        with patch.object(self.app_module, "ask_claude_with_rag", return_value="Test reply"):
            response = self.client.post(
                "/chat",
                data=json.dumps({"message": "what services do you offer?"}),
                content_type="application/json"
            )
        assert response.status_code == 200

    def test_chat_response_has_reply_key(self):
        """/chat response JSON should always contain a 'reply' key"""
        with patch.object(self.app_module, "ask_claude_with_rag", return_value="Test reply"):
            response = self.client.post(
                "/chat",
                data=json.dumps({"message": "tell me about pricing"}),
                content_type="application/json"
            )
        data = json.loads(response.data)
        assert "reply" in data

    def test_chat_response_has_source_key(self):
        """/chat response JSON should always contain a 'source' key"""
        with patch.object(self.app_module, "ask_claude_with_rag", return_value="Test reply"):
            response = self.client.post(
                "/chat",
                data=json.dumps({"message": "tell me about pricing"}),
                content_type="application/json"
            )
        data = json.loads(response.data)
        assert "source" in data

    def test_empty_message_returns_error(self):
        """An empty message should return an error reply"""
        response = self.client.post(
            "/chat",
            data=json.dumps({"message": ""}),
            content_type="application/json"
        )
        data = json.loads(response.data)
        assert "reply" in data
        assert data["source"] == "error"

    def test_greeting_uses_flow_source(self):
        """A greeting message should be handled by the flow, not RAG"""
        response = self.client.post(
            "/chat",
            data=json.dumps({"message": "hello"}),
            content_type="application/json"
        )
        data = json.loads(response.data)
        assert data["source"] == "flow"

    def test_number_input_uses_todo_source(self):
        """A number input should trigger the todo lookup"""
        with patch.object(self.app_module, "build_todo_summary", return_value="Todo summary"):
            response = self.client.post(
                "/chat",
                data=json.dumps({"message": "5"}),
                content_type="application/json"
            )
        data = json.loads(response.data)
        assert data["source"] == "todo"
