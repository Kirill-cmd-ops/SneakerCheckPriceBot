from aiogram import Router
from aiogram.types import CallbackQuery

from sneaker_bot.services.send_head_menu import send_head_menu

router = Router()


@router.callback_query(lambda c: c.data == "back_main")
async def back_head_menu_button(query: CallbackQuery, state: CallbackQuery):
    await query.answer()
    await send_head_menu(
        query,
        state,
        text="📩Выберите дальнейшее действие:📩"
    )
    await query.message.delete()
