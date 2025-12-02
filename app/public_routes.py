from fastapi import APIRouter


def build_public_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return router
