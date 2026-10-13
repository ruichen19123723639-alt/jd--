from typing import TypedDict


class Message(TypedDict):
    role: str
    content: str


# 仅用于学习：程序重启后历史会丢失
conversation_history: dict[str, list[Message]] = {}


def get_messages(
    session_id: str,
    user_message: str,
) -> list[Message]:
    history = conversation_history.get(session_id, [])

    return [
        *history,
        {
            "role": "user",
            "content": user_message,
        },
    ]


def save_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    history = conversation_history.setdefault(
        session_id,
        [],
    )

    history.extend(
        [
            {
                "role": "user",
                "content": user_message,
            },
            {
                "role": "assistant",
                "content": assistant_message,
            },
        ]
    )


def chat(
    session_id: str,
    user_message: str,
) -> str:
    messages = get_messages(
        session_id,
        user_message,
    )

    previous_message_count = len(messages) - 1

    assistant_message = (
        f"会话 {session_id} 收到消息："
        f"{user_message}；"
        f"此前已有 {previous_message_count} 条消息。"
    )

    save_turn(
        session_id,
        user_message,
        assistant_message,
    )

    return assistant_message


def main() -> None:
    chat(
        "user-001",
        "我想找 Python 后端岗位",
    )

    chat(
        "user-002",
        "我想找前端岗位",
    )

    chat(
        "user-001",
        "我还缺哪些技能？",
    )

    user_001_history = conversation_history["user-001"]
    user_002_history = conversation_history["user-002"]

    assert any(
        "Python" in message["content"]
        for message in user_001_history
    )

    assert not any(
        "前端" in message["content"]
        for message in user_001_history
    )

    assert any(
        "前端" in message["content"]
        for message in user_002_history
    )

    assert len(user_001_history) == 4
    assert len(user_002_history) == 2

    print("Memory demo passed")
    print("user-001:", user_001_history)
    print("user-002:", user_002_history)


if __name__ == "__main__":
    main()