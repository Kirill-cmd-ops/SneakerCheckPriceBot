from aiogram.types import CallbackQuery

from sneaker_bot.dependencies import dp
from sneaker_bot.main import send_head_menu


@dp.callback_query(lambda c: c.data == "back_main")
async def back_head_menu_button(query: CallbackQuery, state: CallbackQuery):
    await query.answer()
    await send_head_menu(
        query,
        state,
        text="Выберите дальнейшее действие:"
    )
    await query.message.delete()