import json
import os
import time

import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import BaseModel
from pydantic import BaseModel, Field
from pydantic import BaseModel, Field, ValidationError

load_dotenv(override=True)
from rag_demo import retrieve
class AnalyzeRequest(BaseModel):
    jd: str = Field(min_length=1)


class JobAnalysis(BaseModel):
    job_title: str
    core_skills: list[str]
    responsibilities: list[str]
    bonus_items: list[str]
    risks_or_unknowns: list[str]

class RagAnalysisResponse(BaseModel):
    analysis: JobAnalysis
    sources: list[str]

class MatchRequest(BaseModel):
    required_skills: list[str]
    candidate_skills: list[str]


class MatchResult(BaseModel):
    score: int
    matched_skills: list[str]
    missing_skills: list[str]

class AgentMatchRequest(BaseModel):
    required_skills: list[str]
    candidate_skills: list[str]

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    message: str

app = FastAPI(title="JD 分析助手")
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time_ms = (
        time.perf_counter() - start_time
    ) * 1000

    response.headers["X-Process-Time-ms"] = (
        f"{process_time_ms:.2f}"
    )

    return response

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    timeout=120.0,
)

DATABASE_PATH = Path(__file__).with_name("memory.db")


def init_memory_database() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.commit()


def load_messages(
    session_id: str,
) -> list[dict[str, str]]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()

    return [
        {
            "role": role,
            "content": content,
        }
        for role, content in rows
    ]


def save_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executemany(
            """
            INSERT INTO messages (
                session_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    session_id,
                    "user",
                    user_message,
                    datetime.now().isoformat(),
                ),
                (
                    session_id,
                    "assistant",
                    assistant_message,
                    datetime.now().isoformat(),
                ),
            ],
        )

        connection.commit()


init_memory_database()

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

@app.post("/analyze", response_model=JobAnalysis)
def analyze(request: AnalyzeRequest):
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
{request.jd}
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
        return JobAnalysis.model_validate_json(content)
    except ValidationError as error:
        raise HTTPException(
            status_code=502,
            detail=f"模型返回格式错误：{error}",
        ) from error

@app.post("/rag-analyze", response_model=RagAnalysisResponse)
def rag_analyze(request: AnalyzeRequest):
    with open("profile.txt", "r", encoding="utf-8") as file:
        profile = file.read()

    retrieved_context = retrieve(request.jd, profile, top_k=5)

    if not retrieved_context:
        raise HTTPException(
            status_code=404,
            detail="没有检索到候选人资料，无法可靠分析",
        )

    context = "\n\n".join(
        f"来源：profile.txt\n{paragraph}"
        for paragraph in retrieved_context
    )

    prompt = f"""
你是一名求职分析助手。

请只根据下面提供的候选人资料分析候选人与职位的匹配情况。
不要编造资料中没有出现的经历。
如果资料中没有明确证据，请写“资料中没有明确说明”，不要推测。

请只返回合法 JSON，不要使用 Markdown 代码块，必须包含：
- job_title：岗位名称，字符串
- core_skills：核心技能，字符串数组
- responsibilities：工作职责，字符串数组
- bonus_items：加分项，字符串数组
- risks_or_unknowns：风险或未知信息，字符串数组

职位描述：
{request.jd}

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

    content = (response.choices[0].message.content or "").strip()

    try:
        analysis = JobAnalysis.model_validate_json(content)
    except ValidationError as error:
        raise HTTPException(
        status_code=502,
        detail=f"模型返回格式错误：{error}",
    ) from error

    return {
        "analysis": analysis,
        "sources": ["profile.txt"],
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    history = load_messages(request.session_id)

    messages = [
        {
            "role": "system",
            "content": (
                "你是一名求职学习助手。"
                "请结合当前会话上下文回答问题。"
            ),
        },
        *history,
        {
            "role": "user",
            "content": request.message,
        },
    ]

    response = client.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=messages,
    )

    assistant_message = (
        response.choices[0].message.content or ""
    ).strip()

    save_turn(
    request.session_id,
    request.message,
    assistant_message,
)

    return {
        "session_id": request.session_id,
        "message": assistant_message,
    }

@app.post("/match", response_model=MatchResult)
def match(request: MatchRequest):
    return calculate_match_score(
        required_skills=request.required_skills,
        candidate_skills=request.candidate_skills,
    )
@app.post("/agent-match", response_model=MatchResult)
def agent_match(request: AgentMatchRequest):
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
                "请使用 calculate_match_score 工具计算技能匹配度。"
                f"岗位要求技能：{request.required_skills}。"
                f"候选人技能：{request.candidate_skills}。"
                "必须调用工具，不要自行计算。"
            ),
        }
    ]
    
    try:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                model=os.environ["OPENAI_MODEL"],
                messages=messages,
                tools=tools,
                )
                break
            except (APITimeoutError, APIConnectionError):
                if attempt == 1:
                   raise

            time.sleep(1)

    except APITimeoutError:
        raise HTTPException(
        status_code=504,
        detail="模型连续两次响应超时，请稍后重试",
    )
    except APIConnectionError:
        raise HTTPException(
        status_code=502,
        detail="模型服务连接失败，请稍后重试",
    )
    except APIStatusError as error:
        raise HTTPException(
        status_code=502,
        detail=f"模型服务返回错误：{error.status_code}",
    )

    assistant_message = response.choices[0].message

    if not assistant_message.tool_calls:
        raise HTTPException(
            status_code=502,
            detail="模型没有调用 calculate_match_score 工具",
        )

    tool_call = assistant_message.tool_calls[0]

    try:
        arguments = json.loads(tool_call.function.arguments)

        result = calculate_match_score(
            required_skills=arguments["required_skills"],
            candidate_skills=arguments["candidate_skills"],
        )

        return result

    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=502,
            detail=f"工具参数格式错误：{error}",
        )