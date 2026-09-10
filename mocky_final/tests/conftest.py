"""
Shared fixtures for all test layers (unit / integration / system).
We never call the real Groq API in tests — mock_llm patches the SDK
call so tests are fast, free, and deterministic.
"""
import os
import sys

# Make sure app.py can be imported regardless of where pytest is invoked from
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-dummy-key")

import pytest
import app as mocky_app

# A canned "IBPS RRB style" question in the exact format app.py expects back
# from the LLM. Answer is always (b) so tests can predict correctness.
SAMPLE_REASONING_Q = """Q. Five friends sit in a row facing north. Who sits second from the left?
(a) A
(b) B
(c) C
(d) D
(e) E
ANSWER: (b)"""


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


@pytest.fixture
def mock_llm(monkeypatch):
    """Patches client.chat.completions.create to return a canned question.
    Tests can override the returned text via mock_llm['text'] = "...".
    """
    holder = {"text": SAMPLE_REASONING_Q}

    def fake_create(*args, **kwargs):
        return _FakeCompletion(holder["text"])

    monkeypatch.setattr(mocky_app.client.chat.completions, "create", fake_create)
    return holder


@pytest.fixture
def client(mock_llm):
    """Flask test client with a clean session per test."""
    mocky_app.app.config["TESTING"] = True
    with mocky_app.app.test_client() as c:
        yield c
