import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .chat_model import OllamaChatModel
from .config import ROOT, Settings
from .db import Database
from .model import EmotionModel
from .service import EmotionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)


class CreateChat(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=20000)


def create_app(
    settings: Settings | None = None,
    model: EmotionModel | None = None,
    chat_model: OllamaChatModel | None = None,
) -> FastAPI:
    settings = settings or Settings()
    db = Database(settings.database_path)
    model = model or EmotionModel(settings)
    chat_model = chat_model or OllamaChatModel(settings)
    service = EmotionService(db, model, settings, chat_model)
    token = settings.access_token or secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.initialize()
        LOG.info("Local access URL: http://127.0.0.1:8000/?key=%s", quote(token))
        LOG.info("Loading Laya checkpoint=%s device=%s", settings.checkpoint, settings.device)
        model.load()
        if model.ready:
            LOG.info("Laya ready")
        else:
            LOG.warning("Laya unavailable: %s", model.error)
        LOG.info("Ollama chat model=%s endpoint=%s", settings.ollama_model, settings.ollama_base_url)
        LOG.info("Emotion verifier model=%s", settings.emotion_verifier_model)
        try:
            yield
        finally:
            await chat_model.close()
            if isinstance(model, EmotionModel):
                model.close()

    app = FastAPI(title="Emotion Constellation", lifespan=lifespan)
    app.state.service = service
    app.state.access_token = token

    def authorize(authorization: str | None = Header(default=None)) -> None:
        if not authorization or not secrets.compare_digest(authorization, f"Bearer {token}"):
            raise HTTPException(401, "Enter the local access key shown in the server terminal.")

    @app.get("/api/health")
    async def health():
        evidence_status = await asyncio.to_thread(model.verifier.status) if isinstance(model, EmotionModel) else "ready"
        return {
            "service": "ready",
            "emotion": "ready" if model.ready and evidence_status == "ready" else "unavailable",
            "checkpoint": settings.checkpoint,
            "error": model.error or (f"Emotion verifier {evidence_status}" if evidence_status != "ready" else None),
            "chat": await chat_model.status(),
            "chat_model": settings.ollama_model,
        }

    @app.get("/api/chats", dependencies=[Depends(authorize)])
    def list_chats():
        return service.list_chats()

    @app.post("/api/chats", dependencies=[Depends(authorize)])
    def create_chat(body: CreateChat):
        return service.create_chat(body.title)

    @app.get("/api/chats/{chat_id}", dependencies=[Depends(authorize)])
    def get_chat(chat_id: str):
        chat = service.get_chat(chat_id)
        if not chat:
            raise HTTPException(404, "Conversation not found")
        return chat

    @app.delete("/api/chats/{chat_id}", dependencies=[Depends(authorize)])
    async def delete_chat(chat_id: str):
        if not await service.delete_chat(chat_id):
            raise HTTPException(404, "Conversation not found")
        return {"deleted": True}

    @app.post("/api/chats/{chat_id}/messages", dependencies=[Depends(authorize)])
    async def send_message(chat_id: str, body: SendMessage):
        existing = service.get_chat(chat_id)
        if existing is None:
            raise HTTPException(404, "Conversation not found")
        if existing["source"] == "illustrative":
            raise HTTPException(403, "Illustrative chats are read only. Create a new conversation to send a message.")
        if not body.content.strip():
            raise HTTPException(422, "Message cannot be blank")
        result = await service.add_user_message(chat_id, body.content.strip())
        if result is None:
            raise HTTPException(404, "Conversation not found")
        return result

    @app.get("/api/chats/{chat_id}/emotion", dependencies=[Depends(authorize)])
    def chat_emotion(chat_id: str):
        result = service.chat_emotion(chat_id)
        if result is None:
            raise HTTPException(404, "Conversation not found")
        return result

    @app.get("/api/emotion/analytics", dependencies=[Depends(authorize)])
    def analytics(
        mode: str = Query("final", pattern="^(final|peak|average)$"),
        start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        min_anxiety: float = Query(0, ge=0, le=100),
        min_sadness: float = Query(0, ge=0, le=100),
        min_fear: float = Query(0, ge=0, le=100),
        dominant: str = Query("all", pattern="^(all|anxiety|sadness|fear|mixed|neutral|low)$"),
        search: str = Query("", max_length=120),
    ):
        return service.analytics(
            mode,
            start_date,
            end_date,
            {"anxiety": min_anxiety, "sadness": min_sadness, "fear": min_fear},
            dominant,
            search,
        )

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}")
        def frontend(path: str):
            target = dist / path
            if path and target.is_file() and target.resolve().is_relative_to(dist.resolve()):
                return FileResponse(target)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
