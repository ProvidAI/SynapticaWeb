"""Lightweight FastAPI server exposing local agents over an A2A-inspired API."""

from __future__ import annotations

import inspect
import logging
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from .models import AgentCard, MessagePayload, MessageResponse

logger = logging.getLogger(__name__)


class A2AServer:
    """Expose an internal agent over HTTP with a minimal A2A-compatible surface."""

    def __init__(
        self,
        agent: Any,
        agent_card: AgentCard,
        *,
        host: str = "0.0.0.0",
        port: int = 9000,
        enable_cors: bool = True,
    ):
        self.agent = agent
        self.agent_card = agent_card
        self.host = host
        self.port = port
        self.enable_cors = enable_cors
        self._app: Optional[FastAPI] = None

    def _build_router(self) -> APIRouter:
        """Create the API router implementing the shim."""

        router = APIRouter()

        @router.get("/.well-known/agent.json", response_model=AgentCard)
        async def get_agent_card() -> AgentCard:
            logger.debug("Serving agent card for %s", self.agent_card.id)
            return self.agent_card

        @router.post("/a2a/v1/messages", response_model=MessageResponse)
        async def send_message(payload: MessagePayload) -> MessageResponse:
            message_id = uuid4().hex
            try:
                result = await self._invoke_agent(payload.message, metadata=payload.metadata)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Agent invocation failed for %s", self.agent_card.id)
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            response_text = self._coerce_response(result)
            return MessageResponse(
                message_id=message_id,
                response=response_text,
                metadata={"echo": payload.metadata} if payload.metadata else None,
            )

        return router

    async def _invoke_agent(
        self,
        message: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Call the underlying agent, awaiting as required."""

        candidate: Any

        if hasattr(self.agent, "invoke_async") and callable(self.agent.invoke_async):
            candidate = self.agent.invoke_async(message, metadata=metadata)
        elif hasattr(self.agent, "run") and callable(self.agent.run):
            candidate = self.agent.run(message)
        elif callable(self.agent):
            candidate = self.agent(message)
        else:
            raise RuntimeError(f"Agent {self.agent!r} is not callable")

        if inspect.isawaitable(candidate):
            return await candidate
        return candidate

    @staticmethod
    def _coerce_response(result: Any) -> str:
        """Convert an agent result into a response string."""

        if isinstance(result, str):
            return result
        if result is None:
            return ""
        return str(result)

    def to_fastapi_app(self) -> FastAPI:
        """Build (or memoise) the FastAPI application."""

        if self._app is None:
            app = FastAPI(
                title=self.agent_card.name,
                version=self.agent_card.version,
                description=self.agent_card.description,
            )
            if self.enable_cors:
                app.add_middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
            app.include_router(self._build_router())
            self._app = app
        return self._app

    def serve(self) -> None:
        """Start a uvicorn server hosting the FastAPI application."""

        uvicorn.run(self.to_fastapi_app(), host=self.host, port=self.port, log_level="info")
