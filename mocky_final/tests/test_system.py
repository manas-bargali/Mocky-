"""
SYSTEM TESTS
Exercise the whole app the way a real user/browser would: full exam flow
from landing page through 3 questions to the final result screen, and
session isolation between two different users hitting the server at once.
"""
import pytest
import app as mocky_app


def test_full_exam_flow_start_to_result(client):
    # 1. Land on home page
    assert client.get("/").status_code == 200

    # 2. Start the exam
    start = client.post("/start", json={"section": "Reasoning"})
    assert start.get_json()["status"] == "ok"

    # 3. Answer all 3 questions (sample question's correct answer is always 'b')
    given_answers = ["b", "a", "b"]   # correct, wrong, correct
    for i, ans in enumerate(given_answers, start=1):
        q = client.get("/question")
        assert q.get_json()["q_num"] == i
        submit = client.post("/submit", json={"answer": ans})
        assert submit.get_json()["total"] == i

    # 4. Fetch the final result
    result = client.get("/result")
    data = result.get_json()
    assert data["total"] == 3
    assert data["score"] == 2
    assert data["percent"] == pytest.approx(66.7, rel=0.01)
    assert "grade" in data
    assert len(data["answers"]) == 3


def test_two_concurrent_users_have_isolated_sessions(mock_llm):
    mocky_app.app.config["TESTING"] = True
    user_a = mocky_app.app.test_client()
    user_b = mocky_app.app.test_client()

    user_a.post("/start", json={"section": "Reasoning"})
    user_a.get("/question")
    user_a.post("/submit", json={"answer": "b"})  # user A gets 1 correct

    user_b.post("/start", json={"section": "Quantitative"})
    # user B hasn't answered anything yet

    result_a = user_a.get("/result").get_json()
    result_b = user_b.get("/result").get_json()

    assert result_a["total"] == 1
    assert result_a["score"] == 1
    assert result_b["total"] == 0
    assert result_b["section"] == "Quantitative"
