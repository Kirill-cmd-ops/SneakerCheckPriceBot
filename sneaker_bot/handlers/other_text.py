from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message()
async def other_text(message: Message):
    """
    Удаляем входящие сообщения от пользователя (чтобы чат не засорялся).
    Если нужно — можно дополнительно логировать или сохранять.
    """
    try:
        await message.delete()
    except Exception:
        # игнорируем ошибки удаления (например, если сообщение уже удалено)
        pass
