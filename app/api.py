import hashlib
import hmac
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, Form, Header, HTTPException, Response, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import Settings
from .db import Database


def create_api(settings: Settings, database: Database) -> FastAPI:
    app = FastAPI(title="ReferralBot Backend", version="0.1.0")
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    admin_panel_dir = static_dir / "admin_panel"
    admin_panel_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/admin_panel/static", StaticFiles(directory=admin_panel_dir), name="admin_panel_static")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    def _session_secret() -> str:
        secret = settings.admin_panel_secret or settings.api_key
        if not secret:
            raise RuntimeError("ADMIN_SECRET or API_KEY must be set for admin auth")
        return secret

    def _sign_session(user_id: str) -> str:
        secret = _session_secret().encode()
        digest = hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()
        return f"{user_id}.{digest}"

    def _verify_session(raw: str = None):
        if not raw:
            return None
        try:
            user_id, signature = raw.split(".", 1)
        except ValueError:
            return None
        expected = _sign_session(user_id)
        if hmac.compare_digest(expected, raw):
            return user_id
        return None

    async def verify_admin(
        x_api_key=Header(default=None),
        session=Cookie(default=None),
    ) -> None:
        # Allow header key if set
        if settings.api_key and x_api_key == settings.api_key:
            return
        # Allow session cookie if valid
        if _verify_session(session):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    Auth = Depends(verify_admin)

    async def verify_key(x_api_key=Header(default=None)) -> None:
        if settings.api_key is None:
            return
        if x_api_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/submissions")
    async def submissions(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_submissions(limit=limit)
        return {"items": items, "limit": limit}

    @app.get("/actions")
    async def actions(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_actions(limit=limit)
        return {"items": items, "limit": limit}

    @app.get("/questions")
    async def questions(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_questions(limit=limit)
        return {"items": items, "limit": limit}

    @app.get("/reports")
    async def reports(limit: int = 50, auth: None = Auth) -> dict:
        items = await database.list_reports(limit=limit)
        return {"items": items, "limit": limit}

    @app.post("/questions/{question_id}/reply")
    async def reply_question(question_id: int, message: str, auth: None = Auth) -> dict:
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

    @app.post("/reports/{report_id}/reply")
    async def reply_report(report_id: int, message: str, auth: None = Auth) -> dict:
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
        return {"status": "ok"}

    @app.post("/broadcast")
    async def broadcast(message: str, auth: None = Auth) -> dict:
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

    @app.get("/admin/login", include_in_schema=False)
    async def login_page() -> FileResponse:
        login_file = static_dir / "login.html"
        if not login_file.exists():
            return HTMLResponse("<h1>Login page missing</h1>", status_code=500)
        return FileResponse(login_file)

    @app.post("/admin/login", include_in_schema=False)
    async def login(
        response: Response,
        user_id: Annotated[str, Form()],
        password: Annotated[str, Form()],
    ) -> RedirectResponse:
        if not settings.admin_panel_user_id or not settings.admin_panel_password:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Admin credentials not set")

        valid_id = str(settings.admin_panel_user_id)
        if user_id != valid_id or password != settings.admin_panel_password:
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

    @app.get("/admin/logout", include_in_schema=False)
    async def logout() -> RedirectResponse:
        response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
        response.delete_cookie("session")
        return response

    @app.get("/admin", include_in_schema=False)
    async def admin_page(auth: None = Auth) -> FileResponse:
        admin_file = static_dir / "admin.html"
        if not admin_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin page not found")
        return FileResponse(admin_file)

    @app.get("/admin/panel", include_in_schema=False)
    async def admin_panel(auth: None = Auth) -> FileResponse:
        panel_file = admin_panel_dir / "index.html"
        if not panel_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin panel not found")
        return FileResponse(panel_file)

    return app
