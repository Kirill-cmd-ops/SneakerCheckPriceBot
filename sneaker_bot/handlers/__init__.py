from aiogram import Router

from .start_command import router as start_router
from .back_head_menu_button import router as back_head_menu_router
from check_button import router as check_router
from close_news_button import router as close_news_router
from know_button import router as know_router
from order_button import router as order_router
from other_text import router as other_router
from search_news_button import router as search_news_router


router = Router()


router.include_router(start_router)
router.include_router(back_head_menu_router)
router.include_router(check_router)
router.include_router(close_news_router)
router.include_router(know_router)
router.include_router(order_router)
router.include_router(other_router)
router.include_router(search_news_router)