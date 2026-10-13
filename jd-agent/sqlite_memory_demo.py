import sqlite3
from datetime import datetime
from pathlib import Path


DATABASE_PATH = Path("memory.db")


def init_database(connection):
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


def save_message(
    connection,
    session_id: str,
    role: str,
    content: str,
) -> None:
    connection.execute(
        """
        INSERT INTO messages (
            session_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id,
            role,
            content,
            datetime.now().isoformat(),
        ),
    )

    connection.commit()


def load_messages(
    connection,
    session_id: str,
) -> list[dict[str, str]]:
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


def main():
    connection = sqlite3.connect(DATABASE_PATH)

    init_database(connection)

    session_id = "sqlite-demo-user"

    existing_messages = load_messages(
        connection,
        session_id,
    )

    if not existing_messages:
        save_message(
            connection,
            session_id,
            "user",
            "我的目标岗位是 Python 后端开发",
        )

        save_message(
            connection,
            session_id,
            "assistant",
            "好的，我会记住你的目标岗位",
        )

    messages = load_messages(
        connection,
        session_id,
    )

    print("SQLite Memory demo passed")
    print(messages)

    connection.close()


if __name__ == "__main__":
    main()