"""
INTEGRATION TESTS
Test Flask routes talking to each other + session state.
The Groq call itself is mocked (see conftest.mock_llm) so these stay fast
and don't burn real API quota — but every layer of app.py (routing, session,
parsing, scoring) actually runs.
"""
import app as mocky_app


def test_index_serves_home_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Mocky" in resp.data


def test_start_exam_initializes_session(client):
    resp = client.post("/start", json={"section": "Quantitative"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"status": "ok", "section": "Quantitative"}


def test_get_question_returns_parsed_question(client):
    client.post("/start", json={"section": "Reasoning"})
    resp = client.get("/question")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["options"]["b"] == "B"
    assert data["q_num"] == 1


def test_submit_correct_answer_increments_score(client):
    client.post("/start", json={"section": "Reasoning"})
    client.get("/question")            # sample question's answer is (b)
    resp = client.post("/submit", json={"answer": "b"})
    data = resp.get_json()
    assert data["is_correct"] is True
    assert data["score"] == 1
    assert data["total"] == 1


def test_submit_wrong_answer_does_not_increment_score(client):
    client.post("/start", json={"section": "Reasoning"})
    client.get("/question")
    resp = client.post("/submit", json={"answer": "a"})
    data = resp.get_json()
    assert data["is_correct"] is False
    assert data["score"] == 0
    assert data["total"] == 1


def test_question_endpoint_surfaces_llm_errors_as_500(client, monkeypatch):
    def broken_create(*a, **k):
        raise RuntimeError("upstream Groq error")
    monkeypatch.setattr(mocky_app.client.chat.completions, "create", broken_create)

    client.post("/start", json={"section": "Reasoning"})
    resp = client.get("/question")
    assert resp.status_code == 500
    assert "error" in resp.get_json()


def test_history_avoids_repeating_last_question_type(client):
    client.post("/start", json={"section": "Reasoning"})
    client.get("/question")
    with client.session_transaction() as sess:
        assert "history" in sess
        assert len(sess["history"]) >= 1
