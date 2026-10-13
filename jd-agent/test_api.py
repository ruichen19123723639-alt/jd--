import os
import json
import httpx
import sqlite3
from types import SimpleNamespace
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "https://example.com/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")
from fastapi.testclient import TestClient

import api


client = TestClient(api.app)
error_client = TestClient(
    api.app,
    raise_server_exceptions=False,
)


def test_rag_invalid_model_json():
    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="这不是合法 JSON"
                )
            )
        ]
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: fake_response
            )
        )
    )

    original_client = api.client
    api.client = fake_client

    try:
        response = error_client.post(
            "/rag-analyze",
            json={
                "jd": "招聘 Python FastAPI 后端工程师"
            },
        )
    finally:
        api.client = original_client

    assert response.status_code == 502

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_jd():
    response = client.post("/analyze", json={"jd": ""})
    assert response.status_code == 422


def test_match():
    response = client.post(
        "/match",
        json={
            "required_skills": ["Python", "FastAPI", "Docker"],
            "candidate_skills": ["Python", "Docker"],
        },
    )
    assert response.status_code == 200
    assert response.json()["score"] == 67


def test_rag_without_evidence():
    response = client.post(
        "/rag-analyze",
        json={"jd": "招聘 Kubernetes 运维工程师"},
    )
    assert response.status_code == 404
def test_rag_with_evidence():
    payload = {
        "job_title": "Python 后端工程师",
        "core_skills": ["Python", "FastAPI"],
        "responsibilities": [],
        "bonus_items": [],
        "risks_or_unknowns": [],
    }

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(payload)
                )
            )
        ]
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: fake_response
            )
        )
    )

    original_client = api.client
    api.client = fake_client

    try:
        response = client.post(
            "/rag-analyze",
            json={
                "jd": "招聘 Python FastAPI 后端工程师"
            },
        )
    finally:
        api.client = original_client

    assert response.status_code == 200
    assert response.json()["analysis"]["job_title"] == "Python 后端工程师"
    assert response.json()["sources"] == ["profile.txt"]

def test_analyze_invalid_model_json():
    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="这不是合法 JSON"
                )
            )
        ]
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: fake_response
            )
        )
    )

    original_client = api.client
    api.client = fake_client

    try:
        response = error_client.post(
            "/analyze",
            json={
                "jd": "招聘 Python 后端工程师"
            },
        )
    finally:
        api.client = original_client

    assert response.status_code == 502

def test_agent_match_without_tool_call():
    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[]
                )
            )
        ]
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: fake_response
            )
        )
    )

    original_client = api.client
    api.client = fake_client

    try:
        response = error_client.post(
            "/agent-match",
            json={
                "required_skills": ["Python", "FastAPI"],
                "candidate_skills": ["Python"],
            },
        )
    finally:
        api.client = original_client

    assert response.status_code == 502

def test_agent_match_timeout():
    attempts = [0]

    def timeout_create(**kwargs):
        attempts[0] += 1
        raise api.APITimeoutError(
            request=httpx.Request(
                "POST",
                "https://example.com",
            )
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=timeout_create
            )
        )
    )

    original_client = api.client
    api.client = fake_client

    try:
        response = error_client.post(
            "/agent-match",
            json={
                "required_skills": ["Python", "FastAPI"],
                "candidate_skills": ["Python"],
            },
        )
    finally:
        api.client = original_client

    assert response.status_code == 504
    assert attempts[0] == 2

def test_agent_match_connection_error():
    attempts = [0]

    def connection_error_create(**kwargs):
        attempts[0] += 1
        raise api.APIConnectionError(
            request=httpx.Request(
                "POST",
                "https://example.com",
            )
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=connection_error_create
            )
        )
    )

    original_client = api.client
    api.client = fake_client

    try:
        response = error_client.post(
            "/agent-match",
            json={
                "required_skills": ["Python", "FastAPI"],
                "candidate_skills": ["Python"],
            },
        )
    finally:
        api.client = original_client

    assert response.status_code == 502
    assert attempts[0] == 2

def test_agent_match_invalid_tool_arguments():
    tool_call = SimpleNamespace(
        function=SimpleNamespace(
            arguments="这不是合法 JSON"
        )
    )

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[tool_call]
                )
            )
        ]
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: fake_response
            )
        )
    )

    original_client = api.client
    api.client = fake_client

    try:
        response = error_client.post(
            "/agent-match",
            json={
                "required_skills": ["Python", "FastAPI"],
                "candidate_skills": ["Python"],
            },
        )
    finally:
        api.client = original_client

    assert response.status_code == 502

def test_chat_memory_and_isolation():
    calls = []

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="测试回答"
                )
            )
        ]
    )

    def fake_create(**kwargs):
        calls.append(kwargs["messages"])
        return fake_response

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=fake_create
            )
        )
    )

    original_client = api.client

    with sqlite3.connect(api.DATABASE_PATH) as connection:
        connection.executemany(
         "DELETE FROM messages WHERE session_id = ?",
         [
            ("test-user-001",),
            ("test-user-002",),
         ],
        )
        connection.commit()

    api.client = fake_client

    try:
        first_response = client.post(
            "/chat",
            json={
                "session_id": "test-user-001",
                "message": "我的目标岗位是 Python 后端",
            },
        )

        second_response = client.post(
            "/chat",
            json={
                "session_id": "test-user-001",
                "message": "我的目标岗位是什么？",
            },
        )

        other_user_response = client.post(
            "/chat",
            json={
                "session_id": "test-user-002",
                "message": "我的目标岗位是什么？",
            },
        )
    finally:
        api.client = original_client

        with sqlite3.connect(api.DATABASE_PATH) as connection:
           connection.executemany(
              "DELETE FROM messages WHERE session_id = ?",
              [
                ("test-user-001",),
                ("test-user-002",),
               ],
            )
           connection.commit()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert other_user_response.status_code == 200

    second_request_messages = calls[1]
    other_user_messages = calls[2]

    assert any(
        message["content"] == "我的目标岗位是 Python 后端"
        for message in second_request_messages
    )

    assert not any(
        message["content"] == "我的目标岗位是 Python 后端"
        for message in other_user_messages
    )

def test_response_time_header():
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Process-Time-ms" in response.headers
    assert float(response.headers["X-Process-Time-ms"]) >= 0

if __name__ == "__main__":
    test_health()
    test_empty_jd()
    test_match()
    test_rag_without_evidence()
    test_rag_with_evidence()
    test_rag_invalid_model_json()
    test_analyze_invalid_model_json()
    test_agent_match_without_tool_call()
    test_agent_match_timeout()
    test_agent_match_connection_error()
    test_agent_match_invalid_tool_arguments()
    test_response_time_header()
    test_chat_memory_and_isolation()
    print("API tests passed")

