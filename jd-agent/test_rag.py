from pathlib import Path

from rag_demo import retrieve


profile = Path("profile.txt").read_text(encoding="utf-8")

python_results = retrieve("Python", profile, top_k=5)
assert any("Python能力" in result for result in python_results)

unknown_results = retrieve("Kubernetes", profile, top_k=5)
assert unknown_results == []

print("RAG 检索测试通过：Python 证据命中，无关查询无结果")
