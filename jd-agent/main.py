import os

from openai import OpenAI
from pydantic import BaseModel, ValidationError


class JobAnalysis(BaseModel):
    job_title: str
    core_skills: list[str]
    responsibilities: list[str]
    bonus_items: list[str]
    risks_or_unknowns: list[str]


client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    timeout=30.0,
)

with open("jd.txt", "r", encoding="utf-8") as file:
    jd = file.read()

prompt = f"""
你是一名招聘分析助手。

请分析下面的职位描述，只返回合法 JSON，不要使用 Markdown 代码块。

JSON 必须包含以下字段：
- job_title：岗位名称，字符串
- core_skills：核心技能，字符串数组
- responsibilities：工作职责，字符串数组
- bonus_items：加分项，字符串数组
- risks_or_unknowns：风险或未知信息，字符串数组

职位描述：
{jd}
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

content = (response.choices[0].message.content or "").strip()

try:
    result = JobAnalysis.model_validate_json(content)
    print(result.model_dump_json(ensure_ascii=False, indent=2))
except ValidationError as error:
    print("模型返回的 JSON 不符合预期结构：")
    print(error)
    print("\n模型原始输出：")
    print(content)