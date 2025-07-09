from aiogram.types import CallbackQuery

from sneaker_bot.dependencies import dp
from sneaker_bot.sub_checker import is_sub


@dp.callback_query(lambda c: c.data == "order_button")
@is_sub
async def order_button(query: CallbackQuery):
    await query.answer(
        text="В будущем тут будет ссылка на наш сайт",
        show_alert=True,
    )
    await query.answer()
