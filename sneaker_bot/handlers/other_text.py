from aiogram.types import Message

from sneaker_bot.dependencies import dp


@dp.message()
async def other_text(message: Message):
    try:
        await message.delete()
    except:
        pass