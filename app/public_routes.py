from fastapi import APIRouter
from fastapi.responses import RedirectResponse


def build_public_router() -> APIRouter:
    router = APIRouter()

    @router.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/admin/login")

    @router.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return router
