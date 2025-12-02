import hashlib
import hmac
from pathlib import Path
from typing import Optional, Tuple, List

from fastapi import APIRouter, Cookie, Depends, Form, Header, HTTPException, Response, status, Body
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from .config import Settings
from .db import Database


def build_admin_router(
    settings: Settings,
    database: Database,
    bot,
    static_dir: Path,
    admin_panel_dir: Path,
) -> APIRouter:
    router = APIRouter()

    def _session_secret() -> str:
        secret = settings.admin_panel_secret or settings.api_key
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ADMIN_SECRET or API_KEY must be set for admin auth",
            )
        return secret

    def _allowed_logins() -> List[str]:
        allowed = [login for login, _ in (settings.admin_credentials or [])]
        if settings.admin_panel_user_id:
            allowed.append(str(settings.admin_panel_user_id))
        return allowed

    def _sign_session(user_id: str) -> str:
        secret = _session_secret().encode()
        digest = hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()
        return f"{user_id}.{digest}"

    def _verify_session(raw: Optional[str]):
        if not raw:
            return None
        try:
            user_id, _signature = raw.split(".", 1)
        except ValueError:
            return None
        expected = _sign_session(user_id)
        if not hmac.compare_digest(expected, raw):
            return None
        allowed = _allowed_logins()
        if allowed and user_id not in allowed:
            return None
        return user_id

    async def verify_admin(
        x_api_key=Header(default=None),
        session=Cookie(default=None),
    ) -> None:
        if settings.api_key and x_api_key == settings.api_key:
            return
        if _verify_session(session):
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    Auth = Depends(verify_admin)

    async def _require_credentials() -> List[Tuple[str, str]]:
        pairs = settings.admin_credentials or []
        if settings.admin_panel_user_id and settings.admin_panel_password:
            pairs.append((str(settings.admin_panel_user_id), settings.admin_panel_password))
        if not pairs:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin credentials not set",
            )
        return pairs

    @router.get("/submissions")
    async def submissions(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_submissions(limit=limit)
        return {"items": items, "limit": limit}

    @router.get("/actions")
    async def actions(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_actions(limit=limit)
        return {"items": items, "limit": limit}

    @router.get("/questions")
    async def questions(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_questions(limit=limit)
        return {"items": items, "limit": limit}

    @router.get("/reports")
    async def reports(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_reports(limit=limit)
        return {"items": items, "limit": limit}

    @router.get("/stats/users")
    async def stats_users(auth: None = Auth) -> dict:
        total = await database.count_users_all()
        week = await database.count_users_last_week()
        return {"total": total, "week": week}

    @router.post("/questions/{question_id}/reply")
    async def reply_question(
        question_id: int,
        message: str = Body("", embed=True),
        auth: None = Auth,
    ) -> dict:
        question = await database.get_question(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        user_id = question.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No user_id to reply")
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to send: {e}")
        await database.add_action(
            action="question_reply",
            user_id=user_id,
            username=question.get("username"),
            details={"question_id": question_id, "message": message},
        )
        return {"status": "ok"}

    @router.post("/reports/{report_id}/reply")
    async def reply_report(
        report_id: int,
        message: str = Body("", embed=True),
        auth: None = Auth,
    ) -> dict:
        report = await database.get_report(report_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        user_id = report.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No user_id to reply")
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to send: {e}")
        await database.add_action(
            action="report_reply",
            user_id=user_id,
            username=report.get("username"),
            details={"report_id": report_id, "message": message},
        )
        await database.delete_report(report_id)
        return {"status": "ok"}

    @router.post("/broadcast")
    async def broadcast(
        message: str = Body("", embed=True),
        auth: None = Auth,
    ) -> dict:
        ids = await database.list_all_user_ids()
        sent = 0
        failed = 0
        for uid in ids:
            try:
                await bot.send_message(chat_id=uid, text=message)
                sent += 1
            except Exception:
                failed += 1
        await database.add_action(
            action="broadcast",
            user_id=None,
            username=None,
            details={"message": message, "sent": sent, "failed": failed},
        )
        return {"status": "ok", "sent": sent, "failed": failed, "total": len(ids)}

    @router.post("/cards")
    async def add_card(
        title: str = Body(..., embed=True),
        category: str = Body(..., embed=True),
        payout: str = Body(..., embed=True),
        note: str = Body("", embed=True),
        auth: None = Auth,
    ) -> dict:
        # Сохраняем как действие для журналирования
        await database.add_action(
            action="card_added",
            user_id=None,
            username=None,
            details={"title": title, "category": category, "payout": payout, "note": note},
        )
        return {"status": "ok"}

    @router.post("/questions/{question_id}/reject")
    async def reject_question(question_id: int, auth: None = Auth) -> dict:
        await database.delete_question(question_id)
        await database.add_action(
            action="question_rejected",
            user_id=None,
            username=None,
            details={"question_id": question_id},
        )
        return {"status": "ok"}

    @router.post("/reports/{report_id}/reject")
    async def reject_report(report_id: int, auth: None = Auth) -> dict:
        await database.delete_report(report_id)
        await database.add_action(
            action="report_rejected",
            user_id=None,
            username=None,
            details={"report_id": report_id},
        )
        return {"status": "ok"}

    @router.get("/admin/login", include_in_schema=False)
    async def login_page() -> FileResponse:
        login_file = static_dir / "login.html"
        if not login_file.exists():
            return HTMLResponse("<h1>Login page missing</h1>", status_code=500)
        return FileResponse(login_file)

    @router.post("/admin/login", include_in_schema=False)
    async def login(
        response: Response,
        user_id: str = Form(...),
        password: str = Form(...),
        pairs=Depends(_require_credentials),
    ) -> RedirectResponse:
        match = next((p for p in pairs if p[0] == user_id and p[1] == password), None)
        if not match:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = _sign_session(user_id)
        response = RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )
        return response

    @router.get("/admin/logout", include_in_schema=False)
    async def logout() -> RedirectResponse:
        response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
        response.delete_cookie("session")
        return response

    @router.get("/admin", include_in_schema=False)
    async def admin_page(auth: None = Auth) -> FileResponse:
        panel_file = admin_panel_dir / "index.html"
        if not panel_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin page not found")
        return FileResponse(panel_file)

    @router.get("/admin/panel", include_in_schema=False)
    async def admin_panel(auth: None = Auth) -> FileResponse:
        return await admin_page(auth=auth)

    return router
