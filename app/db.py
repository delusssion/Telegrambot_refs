import json
import os
from typing import Any, Dict, List

import aiosqlite


class Database:
    def __init__(self, path: str):
        self.path = path

    async def connect(self) -> aiosqlite.Connection:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        conn = await aiosqlite.connect(self.path)
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def init_db(self) -> None:
        db = await self.connect()
        try:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    bank TEXT NOT NULL,
                    comment TEXT,
                    file_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    message TEXT,
                    file_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    message TEXT,
                    file_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await db.commit()
        finally:
            await db.close()

    async def add_submission(
        self,
        user_id: int,
        username: str | None,
        bank: str,
        comment: str | None,
        file_id: str | None,
    ) -> int:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                INSERT INTO submissions (user_id, username, bank, comment, file_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, bank, comment, file_id),
            )
            await db.commit()
            return cursor.lastrowid
        finally:
            await db.close()

    async def list_submissions(self, limit: int = 50) -> List[Dict[str, Any]]:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT id, user_id, username, bank, comment, file_id, status, created_at
                FROM submissions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "bank": row[3],
                    "comment": row[4],
                    "file_id": row[5],
                    "status": row[6],
                    "created_at": row[7],
                }
                for row in rows
            ]
        finally:
            await db.close()

    async def add_action(
        self,
        action: str,
        user_id: int | None,
        username: str | None,
        details: Dict[str, Any] | None = None,
    ) -> int:
        serialized = json.dumps(details or {})
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                INSERT INTO actions (user_id, username, action, details)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, action, serialized),
            )
            await db.commit()
            return cursor.lastrowid
        finally:
            await db.close()

    async def list_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT id, user_id, username, action, details, created_at
                FROM actions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "action": row[3],
                    "details": json.loads(row[4] or "{}"),
                    "created_at": row[5],
                }
                for row in rows
            ]
        finally:
            await db.close()

    async def add_question(
        self,
        user_id: int | None,
        username: str | None,
        message: str,
        file_id: str | None = None,
    ) -> int:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                INSERT INTO questions (user_id, username, message, file_id)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, message, file_id),
            )
            await db.commit()
            return cursor.lastrowid
        finally:
            await db.close()

    async def get_question(self, question_id: int) -> Dict[str, Any] | None:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT id, user_id, username, message, file_id, created_at
                FROM questions WHERE id = ?
                """,
                (question_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "username": row[2],
                "message": row[3],
                "file_id": row[4],
                "created_at": row[5],
            }
        finally:
            await db.close()

    async def list_questions(self, limit: int = 50) -> List[Dict[str, Any]]:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT id, user_id, username, message, file_id, created_at
                FROM questions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "message": row[3],
                    "file_id": row[4],
                    "created_at": row[5],
                }
                for row in rows
            ]
        finally:
            await db.close()

    async def add_report(
        self,
        user_id: int | None,
        username: str | None,
        message: str | None,
        file_id: str | None = None,
    ) -> int:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                INSERT INTO reports (user_id, username, message, file_id)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, message, file_id),
            )
            await db.commit()
            return cursor.lastrowid
        finally:
            await db.close()

    async def get_report(self, report_id: int) -> Dict[str, Any] | None:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT id, user_id, username, message, file_id, created_at
                FROM reports WHERE id = ?
                """,
                (report_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "username": row[2],
                "message": row[3],
                "file_id": row[4],
                "created_at": row[5],
            }
        finally:
            await db.close()

    async def list_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT id, user_id, username, message, file_id, created_at
                FROM reports
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "message": row[3],
                    "file_id": row[4],
                    "created_at": row[5],
                }
                for row in rows
            ]
        finally:
            await db.close()

    async def list_all_user_ids(self) -> List[int]:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT DISTINCT user_id FROM (
                    SELECT user_id FROM submissions
                    UNION ALL
                    SELECT user_id FROM actions
                    UNION ALL
                    SELECT user_id FROM questions
                    UNION ALL
                    SELECT user_id FROM reports
                )
                WHERE user_id IS NOT NULL
                """
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows if row[0] is not None]
        finally:
            await db.close()
