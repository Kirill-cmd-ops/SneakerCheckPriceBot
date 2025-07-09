from aiogram import Router
from aiogram.types import CallbackQuery

from sneaker_bot.menu.head_menu import head_menu
from sneaker_bot.services.send_messages import record_and_send
from sneaker_bot.sub_checker import is_sub


router = Router()

@router.callback_query(lambda c: c.data == "check_button")
@is_sub
async def check_button(query: CallbackQuery, state: CallbackQuery):
    await query.answer()
    await record_and_send(
        query,
        state,
        text="""
            Привет, спасибо за подписку на канал!
    Тут будет публиковаться полезная и интересная информация
    Выберите действие:
            """,
        reply_markup=head_menu
    )
    await query.message.delete()