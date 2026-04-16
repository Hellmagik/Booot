from aiogram import Router

from .admin_support import router as admin_support_router
from .common import router as common_router


router = Router()
router.include_router(common_router)
router.include_router(admin_support_router)

__all__ = ["router"]
