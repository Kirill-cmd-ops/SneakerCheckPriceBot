# handlers/back_head_menu_button.py
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from sneaker_bot.services.send_head_menu import send_head_menu
from sneaker_bot.services.utils import delete_all_prompts_and_sticker

router = Router()


@router.callback_query(lambda c: c.data == "back_main")
async def back_head_menu_button(query: CallbackQuery, state):
    try:
        await query.answer(cache_time=2)
    except TelegramBadRequest:
        pass

    try:
        await delete_all_prompts_and_sticker(state, query.bot)
    except Exception:
        pass

    sent = await send_head_menu(
        query,
        state,
        text="📩Выберите дальнейшее действие:📩"
    )

    try:
        await query.message.delete()
    except TelegramBadRequest:
        pass

    try:
        await state.update_data(menu_msg_id=sent.message_id)
    except Exception:
        pass
