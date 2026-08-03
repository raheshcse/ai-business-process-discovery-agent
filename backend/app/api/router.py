from fastapi import APIRouter

from app.api.routes.analyses import router as analyses_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.documents import router as documents_router
from app.api.routes.governance import router as governance_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router


api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(projects_router)
api_router.include_router(documents_router)
api_router.include_router(analyses_router)
api_router.include_router(governance_router)
