from aiogram import Router

from .start_command import router as start_router


router = Router()


router.include_router(start_router)