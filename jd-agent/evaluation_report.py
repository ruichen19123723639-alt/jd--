import json
import os
import statistics

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "https://example.com/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")

from fastapi.testclient import TestClient

from api import app, calculate_match_score
from pathlib import Path

from rag_demo import retrieve
from datetime import datetime

def evaluate_match_cases():
    with open("test_cases.json", "r", encoding="utf-8") as file:
        test_cases = json.load(file)

    passed = 0

    for case in test_cases:
        result = calculate_match_score(
            required_skills=case["required_skills"],
            candidate_skills=case["candidate_skills"],
        )

        if result["score"] == case["expected_score"]:
            passed += 1

    total = len(test_cases)

    return {
        "total": total,
        "passed": passed,
        "rate": passed / total * 100 if total else 0,
    }


def measure_latency(request_function, count=20):
    latencies = []

    for _ in range(count):
        response = request_function()
        assert response.status_code == 200

        latency = float(
            response.headers["X-Process-Time-ms"]
        )
        latencies.append(latency)

    return {
        "count": len(latencies),
        "average": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "minimum": min(latencies),
        "maximum": max(latencies),
    }

def evaluate_rag_cases():
    profile = Path(
        "profile.txt"
    ).read_text(encoding="utf-8")

    cases = [
        {
            "query": "Python",
            "must_contain": "Python能力",
        },
        {
            "query": "Kubernetes",
            "must_contain": None,
        },
    ]

    passed = 0

    for case in cases:
        results = retrieve(
            case["query"],
            profile,
            top_k=5,
        )

        if case["must_contain"]:
            is_passed = any(
                case["must_contain"] in result
                for result in results
            )
        else:
            is_passed = results == []

        if is_passed:
            passed += 1

    return {
        "total": len(cases),
        "passed": passed,
        "rate": passed / len(cases) * 100,
    }

def main():
    match_report = evaluate_match_cases()
    rag_report = evaluate_rag_cases()

    client = TestClient(app)

    health_report = measure_latency(
        lambda: client.get("/health")
    )

    match_latency_report = measure_latency(
        lambda: client.post(
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
    )
    report = {
    "generated_at": datetime.now().astimezone().isoformat(),
    "match_evaluation": match_report,
    "rag_evaluation": rag_report,
    "latency_ms": {
        "health": health_report,
        "match": match_latency_report,
    },
}

    Path("evaluation_report.json").write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== 技能匹配评估 ===")
    print(
        f"通过率：{match_report['passed']}/"
        f"{match_report['total']} "
        f"= {match_report['rate']:.0f}%"
    )
    print("\n=== RAG 检索评估 ===")
    print(
        f"通过率：{rag_report['passed']}/"
        f"{rag_report['total']} "
        f"= {rag_report['rate']:.0f}%"
    )

    print("\n=== 接口耗时评估 ===")

    print(
        f"/health 平均耗时："
        f"{health_report['average']:.2f} ms"
    )
    print(
        f"/health 中位数耗时："
        f"{health_report['median']:.2f} ms"
    )

    print(
        f"/match 平均耗时："
        f"{match_latency_report['average']:.2f} ms"
    )
    print(
        f"/match 中位数耗时："
        f"{match_latency_report['median']:.2f} ms"
    )
    print("\n评估报告已保存：evaluation_report.json")


if __name__ == "__main__":
    main()