from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from sneaker_bot.dependencies import dp
from sneaker_bot.main import send_head_menu


@dp.callback_query(lambda c: c.data == "close_news")
async def close_news_button(query: CallbackQuery, state: FSMContext):
    await query.answer()
    sent = await send_head_menu(
        query,
        state,
        text="Выберите дальнейшее действие:",
    )
    await state.update_data(menu_msg_id=sent.message_id)
    await query.message.delete()