from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from sneaker_bot.services.send_head_menu import send_head_menu

router = Router()


@router.callback_query(lambda c: c.data == "back_main")
async def back_head_menu_button(query: CallbackQuery, state):
    # подтверждаем нажатие сразу
    try:
        await query.answer(cache_time=2)
    except TelegramBadRequest:
        pass

    # отправляем меню
    await send_head_menu(
        query,
        state,
        text="📩Выберите дальнейшее действие:📩"
    )

    # удаляем старое сообщение
    try:
        await query.message.delete()
    except TelegramBadRequest:
        pass
