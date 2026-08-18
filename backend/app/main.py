import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal, ensure_schema

logger = logging.getLogger(__name__)


async def _restore_vector_index() -> None:
    """Rebuild the in-memory vector index from stored files on startup.

    The vector store is in-process, so every restart would otherwise leave
    documents marked `indexed` in the database with nothing retrievable
    behind them -- analyses would be blocked for want of evidence with no
    visible cause.
    """
    from app.models.document import Document, DocumentIndexStatus
    from app.services.indexing_service import IndexingService

    session = SessionLocal()
    try:
        document_ids = [
            document_id
            for (document_id,) in session.query(Document.id)
            .filter(
                Document.index_status.in_(
                    (
                        DocumentIndexStatus.INDEXED.value,
                        DocumentIndexStatus.PROCESSING.value,
                    )
                )
            )
            .all()
        ]
        if not document_ids:
            return
        logger.info(
            "Restoring vector index for %s document(s) in the background",
            len(document_ids),
        )
        service = IndexingService(session)
        for document_id in document_ids:
            await service.index_document(document_id)
        logger.info("Vector index restore complete")
    except asyncio.CancelledError:
        logger.info("Vector index restore cancelled during shutdown")
        raise
    except Exception:
        logger.exception("Vector index restore failed; documents may need reindexing")
    finally:
        session.close()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_schema()

    # Deliberately not awaited. Re-embedding every stored document can take
    # minutes against a CPU-bound model, and uvicorn does not accept
    # connections until startup returns -- awaiting this made the API look
    # like it had crashed ("connection refused") while it was in fact busy.
    # The task reference is held so it is not garbage collected mid-flight.
    restore_task = asyncio.create_task(_restore_vector_index())

    print(f"Starting {settings.app_name}")
    yield
    if not restore_task.done():
        restore_task.cancel()
        try:
            await restore_task
        except (asyncio.CancelledError, Exception):  # noqa: B014 - shutdown path
            pass
    print(f"Stopping {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for discovering, analysing, and governing "
        "business processes using AI agents."
    ),
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix=settings.api_prefix,
)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "message": settings.app_name,
        "documentation": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
