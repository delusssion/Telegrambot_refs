import json
import os
from typing import Any, Dict, List, Optional

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

                CREATE TABLE IF NOT EXISTS dialogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    status TEXT DEFAULT 'open',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS dialog_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dialog_id INTEGER NOT NULL,
                    direction TEXT NOT NULL, -- 'user' or 'admin'
                    message TEXT,
                    file_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(dialog_id) REFERENCES dialogs(id) ON DELETE CASCADE
                );
                """
            )
            await db.commit()
        finally:
            await db.close()

    async def add_submission(
        self,
        user_id: int,
        username: Optional[str],
        bank: str,
        comment: Optional[str],
        file_id: Optional[str],
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
        user_id: Optional[int],
        username: Optional[str],
        details: Optional[Dict[str, Any]] = None,
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
        user_id: Optional[int],
        username: Optional[str],
        message: str,
        file_id: Optional[str] = None,
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

    async def get_question(self, question_id: int) -> Optional[Dict[str, Any]]:
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

    async def delete_question(self, question_id: int) -> None:
        db = await self.connect()
        try:
            await db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            await db.commit()
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
        user_id: Optional[int],
        username: Optional[str],
        message: Optional[str],
        file_id: Optional[str] = None,
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

    async def delete_report(self, report_id: int) -> None:
        db = await self.connect()
        try:
            await db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
            await db.commit()
        finally:
            await db.close()

    async def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
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

    async def count_users_all(self) -> int:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT user_id, created_at FROM submissions
                    UNION ALL
                    SELECT user_id, created_at FROM actions
                    UNION ALL
                    SELECT user_id, created_at FROM questions
                    UNION ALL
                    SELECT user_id, created_at FROM reports
                )
                WHERE user_id IS NOT NULL
                """
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        finally:
            await db.close()

    async def count_users_last_week(self) -> int:
        db = await self.connect()
        try:
            cursor = await db.execute(
                """
                SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT user_id, created_at FROM submissions
                    UNION ALL
                    SELECT user_id, created_at FROM actions
                    UNION ALL
                    SELECT user_id, created_at FROM questions
                    UNION ALL
                    SELECT user_id, created_at FROM reports
                )
                WHERE user_id IS NOT NULL
                  AND created_at >= datetime('now', '-7 day')
                """
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        finally:
            await db.close()

    async def get_or_create_dialog(self, user_id: int, username: Optional[str]) -> int:
        db = await self.connect()
        try:
            cursor = await db.execute(
                "SELECT id FROM dialogs WHERE user_id = ? AND status = 'open' ORDER BY updated_at DESC LIMIT 1",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row:
                dialog_id = row[0]
            else:
                cur = await db.execute(
                    "INSERT INTO dialogs (user_id, username, status) VALUES (?, ?, 'open')",
                    (user_id, username),
                )
                dialog_id = cur.lastrowid
                await db.commit()
            return dialog_id
        finally:
            await db.close()

    async def add_dialog_message(self, dialog_id: int, direction: str, message: str = "", file_id: Optional[str] = None) -> int:
        db = await self.connect()
        try:
            cur = await db.execute(
                "INSERT INTO dialog_messages (dialog_id, direction, message, file_id) VALUES (?, ?, ?, ?)",
                (dialog_id, direction, message, file_id),
            )
            await db.execute("UPDATE dialogs SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (dialog_id,))
            await db.commit()
            return cur.lastrowid
        finally:
            await db.close()

    async def list_dialogs(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        db = await self.connect()
        try:
            query = """
                SELECT d.id, d.user_id, d.username, d.status, d.created_at, d.updated_at,
                    (SELECT message FROM dialog_messages dm WHERE dm.dialog_id = d.id ORDER BY dm.created_at DESC LIMIT 1) as last_message
                FROM dialogs d
            """
            params: List[Any] = []
            if status:
                query += " WHERE d.status = ?"
                params.append(status)
            query += " ORDER BY d.updated_at DESC LIMIT ?"
            params.append(limit)
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "username": r[2],
                    "status": r[3],
                    "created_at": r[4],
                    "updated_at": r[5],
                    "last_message": r[6],
                }
                for r in rows
            ]
        finally:
            await db.close()

    async def get_dialog(self, dialog_id: int) -> Optional[Dict[str, Any]]:
        db = await self.connect()
        try:
            cur = await db.execute(
                "SELECT id, user_id, username, status, created_at, updated_at FROM dialogs WHERE id = ?",
                (dialog_id,),
            )
            d = await cur.fetchone()
            if not d:
                return None
            cur = await db.execute(
                "SELECT id, direction, message, file_id, created_at FROM dialog_messages WHERE dialog_id = ? ORDER BY created_at ASC",
                (dialog_id,),
            )
            msgs_rows = await cur.fetchall()
            messages = [
                {"id": m[0], "direction": m[1], "message": m[2], "file_id": m[3], "created_at": m[4]}
                for m in msgs_rows
            ]
            return {
                "id": d[0],
                "user_id": d[1],
                "username": d[2],
                "status": d[3],
                "created_at": d[4],
                "updated_at": d[5],
                "messages": messages,
            }
        finally:
            await db.close()

    async def set_dialog_status(self, dialog_id: int, status: str) -> None:
        db = await self.connect()
        try:
            await db.execute("UPDATE dialogs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, dialog_id))
            await db.commit()
        finally:
            await db.close()

    async def delete_dialog(self, dialog_id: int) -> None:
        db = await self.connect()
        try:
            await db.execute("DELETE FROM dialogs WHERE id = ?", (dialog_id,))
            await db.commit()
        finally:
            await db.close()
