import os
import re

from openai import OpenAI


def retrieve(query: str, document: str, top_k: int = 3) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", document)
        if paragraph.strip()
    ]

    terms = set(re.findall(r"[A-Za-z][A-Za-z0-9+#.-]*", query.lower()))

    scored_paragraphs = []
    for paragraph in paragraphs:
        paragraph_lower = paragraph.lower()
        score = sum(term in paragraph_lower for term in terms)
        scored_paragraphs.append((score, paragraph))

    scored_paragraphs.sort(reverse=True)

    return [
        f"[匹配分数：{score}]\n{paragraph}"
        for score, paragraph in scored_paragraphs[:top_k]
        if score > 0
    ]


def main() -> None:
    with open("jd.txt", "r", encoding="utf-8") as file:
        jd = file.read()

    with open("profile.txt", "r", encoding="utf-8") as file:
        profile = file.read()

    retrieved_context = retrieve(jd, profile, top_k=5)

    if not retrieved_context:
        print("没有检索到相关候选人资料，无法可靠分析。")
        raise SystemExit(0)

    print("检索到的候选人资料：")
    print("\n\n".join(retrieved_context))

    context = "\n\n".join(
        f"来源：profile.txt\n{paragraph}"
        for paragraph in retrieved_context
    )

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
        timeout=120.0,
    )

    prompt = f"""
你是一名求职分析助手。

请只根据“候选人资料”分析候选人与职位的匹配情况。
不要编造资料中没有出现的经历。
如果资料中没有明确证据，请写“资料中没有明确说明”，不要推测。
请输出：
1. 已匹配能力
2. 能力不足
3. 建议学习方向
4. 资料依据

职位描述：
{jd}

候选人资料：
{context}
"""

    response = client.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    print("\n模型分析结果：")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
