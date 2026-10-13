import os
import statistics

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "https://example.com/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")

from fastapi.testclient import TestClient

import api


client = TestClient(api.app)
latencies = []

for _ in range(20):
    response = client.get("/health")

    assert response.status_code == 200

    latency_ms = float(
        response.headers["X-Process-Time-ms"]
    )
    latencies.append(latency_ms)

print(f"请求次数：{len(latencies)}")
print(f"最小耗时：{min(latencies):.2f} ms")
print(f"最大耗时：{max(latencies):.2f} ms")
print(f"平均耗时：{statistics.mean(latencies):.2f} ms")
print(f"中位数耗时：{statistics.median(latencies):.2f} ms")

match_latencies = []

for _ in range(20):
    response = client.post(
        "/match",
        json={
            "required_skills": [
                "Python",
                "FastAPI",
                "Docker",
            ],
            "candidate_skills": [
                "Python",
                "Docker",
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] == 67

    latency_ms = float(
        response.headers["X-Process-Time-ms"]
    )
    match_latencies.append(latency_ms)

print("\n/match")
print(f"请求次数：{len(match_latencies)}")
print(f"最小耗时：{min(match_latencies):.2f} ms")
print(f"最大耗时：{max(match_latencies):.2f} ms")
print(f"平均耗时：{statistics.mean(match_latencies):.2f} ms")
print(f"中位数耗时：{statistics.median(match_latencies):.2f} ms")