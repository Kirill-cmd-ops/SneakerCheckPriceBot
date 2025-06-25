import asyncio
import os
from dotenv import load_dotenv



from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

load_dotenv()
BOT_TOKEN = os.getenv("SECRET_TOKEN_BOT")
ID_CHANNEL = os.getenv("ID_CHANNEL")

sub_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Подписаться на канал",
                url="https://t.me/SneakerPriceCheck"
            )
        ],
        [
            InlineKeyboardButton(
                text="Проверить",
                callback_data="check_button"
            )
        ]
    ]
)

head_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Узнать цены",
                callback_data="know_button"
            ),
            InlineKeyboardButton(
                text="Избранное",
                callback_data="favorite_button"
            )
        ],
        [
            InlineKeyboardButton(
                text="Новости",
                callback_data="news_button"
            ),
            InlineKeyboardButton(
                text="Помощь",
                url="tg://resolve?domain=SkForbes"
            )
        ],
        [
            InlineKeyboardButton(
                text="Заказать кроссовки",
                callback_data="order_button"
            )
        ]
    ]
)

back_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data="back_main"
            )
        ]
    ]
)

know_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Добавить в избранное",
                callback_data="back_main"
            )
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data="back_main"
            )
        ]
    ]
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


async def is_sub(bot: Bot, user_id: int) -> bool:
    member = await bot.get_chat_member(
        chat_id=ID_CHANNEL,
        user_id=user_id,
    )
    return member.status not in ("left", "kicked")


@dp.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id

    data = await state.get_data()
    old_menu_id = data.get("menu_msg_id")
    if old_menu_id:
        try:
            await bot.delete_message(message.chat.id, old_menu_id)
        except Exception:
            pass

    if not await is_sub(bot, user_id):
        sent = await message.answer(
            "Чтобы пользоваться, подпишись на канал",
            reply_markup=sub_menu,
        )
    else:
        sent = await message.answer(
            text="Выберите интересующий пункт меню:",
            reply_markup=head_menu
        )

    # 3) сохраняем ID этого меню в FSM
    await state.update_data(menu_msg_id=sent.message_id)


# проверка на подписку
@dp.callback_query(lambda c: c.data == "check_button")
async def check_button(query: CallbackQuery):
    if not await is_sub(bot, query.from_user.id):
        return await query.answer(
            text="Вы не подписаны на канал",
            show_alert=True,
        )
    await query.message.delete()
    await query.answer()
    await query.message.answer(
        text="Привет",
        reply_markup=head_menu
    )


# обработчик кнопки узнать цены
@dp.callback_query(lambda c: c.data == "know_button")
async def know_button(query: CallbackQuery):
    await query.message.delete()
    await query.answer()
    await query.message.answer(
        text="Узнаем цены..."
    )

    await query.message.answer(
        text="""
        Цены вашего товара:
        ...
        ...
        ...""",
        reply_markup=know_menu,
    )


# обработчик кнопки заказать кроссовки
@dp.callback_query(lambda c: c.data == "order_button")
async def order_button(query: CallbackQuery):
    await query.answer(
        text="В будущем тут будет ссылка на наш сайт",
        show_alert=True,
    )
    await query.answer()


@dp.callback_query(lambda c: c.data == "news_button")
async def news_button(query: CallbackQuery):
    pass

# обработчик кнопки назад
@dp.callback_query(lambda c: c.data == "back_main")
async def back_main_button(query: CallbackQuery):
    await query.answer()
    await query.message.answer(
        text="Выберите пункт меню:",
        reply_markup=head_menu
    )


async def main():
    await dp.start_polling(bot, skip_updates=False)


if __name__ == '__main__':
    asyncio.run(main())
