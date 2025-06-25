import asyncio
import os
from dotenv import load_dotenv

from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
async def start_command(message: Message):
    if not await is_sub(bot, message.from_user.id):
        return await message.answer(
            "Чтобы пользоваться данным ботом, подпишись на наш канал",
            reply_markup=sub_menu,
        )
    return await message.answer("Привет")


@dp.callback_query(lambda c: c.data == "check_button")
async def check_button(query: CallbackQuery):
    if not await is_sub(bot, query.from_user.id):
        return await query.answer(
            text="Вы не подписаны на канал",
            show_alert=True,
        )
    await query.answer()
    await query.message.answer(text="Привет, спасибо за подписку")

async def main():
    await dp.start_polling(bot, skip_updates=False)


if __name__ == '__main__':
    asyncio.run(main())
