import json
import os

from openai import OpenAI


def calculate_match_score(
    required_skills: list[str],
    candidate_skills: list[str],
) -> dict:
    candidate_set = {
        skill.strip().lower()
        for skill in candidate_skills
    }

    matched = [
        skill
        for skill in required_skills
        if skill.strip().lower() in candidate_set
    ]

    missing = [
        skill
        for skill in required_skills
        if skill.strip().lower() not in candidate_set
    ]

    score = round(
        len(matched) / len(required_skills) * 100
    ) if required_skills else 100

    return {
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
    }


client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    timeout=30.0,
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_match_score",
            "description": "计算候选人技能与岗位要求的匹配度",
            "parameters": {
                "type": "object",
                "properties": {
                    "required_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "candidate_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "required_skills",
                    "candidate_skills",
                ],
                "additionalProperties": False,
            },
        },
    }
]

messages = [
    {
        "role": "user",
        "content": (
            "请分析岗位和候选人的技能匹配度。"
            "必须调用 calculate_match_score 工具。"
            "岗位要求：Python、FastAPI、RAG、Docker。"
            "候选人技能：Python、FastAPI、RAG、Git。"
        ),
    }
]

first_response = client.chat.completions.create(
    model=os.environ["OPENAI_MODEL"],
    messages=messages,
    tools=tools,
)

assistant_message = first_response.choices[0].message

if not assistant_message.tool_calls:
    print("模型没有调用工具，模型回复：")
    print(assistant_message.content)
else:
    messages.append(
        assistant_message.model_dump(exclude_none=True)
    )

    for tool_call in assistant_message.tool_calls:
        arguments = json.loads(tool_call.function.arguments)

        result = calculate_match_score(
            required_skills=arguments["required_skills"],
            candidate_skills=arguments["candidate_skills"],
        )

        print("工具收到的参数：")
        print(json.dumps(arguments, ensure_ascii=False, indent=2))

        print("\nPython 工具执行结果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    result,
                    ensure_ascii=False,
                ),
            }
        )

    final_response = client.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=messages,
        tools=tools,
    )

    print("\n模型最终回答：")
    print(final_response.choices[0].message.content)