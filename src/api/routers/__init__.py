from fastapi import APIRouter

from .auth import router as auth_router
from .chat import router_chat
from .history import router_history
from .invitations import router as invitation_router
from .seo import router_seo

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(router_seo)
router.include_router(router_chat)
router.include_router(router_history)
router.include_router(invitation_router)
