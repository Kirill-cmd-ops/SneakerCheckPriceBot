from aiogram import Router

from aiogram.types import Message

router = Router()


@router.message()
async def other_text(message: Message):
    try:
        await message.delete()
    except:
        pass
