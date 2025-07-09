from aiogram import Router

from aiogram.types import CallbackQuery

from sneaker_bot.sub_checker import is_sub

router = Router()


@router.callback_query(lambda c: c.data == "order_button")
@is_sub
async def order_button(query: CallbackQuery):
    await query.answer(
        text="В будущем тут будет ссылка на наш сайт",
        show_alert=True,
    )
    await query.answer()
