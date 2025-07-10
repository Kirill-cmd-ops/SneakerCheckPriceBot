from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

back_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚪Назад🚪",
                callback_data="back_main"
            )
        ]
    ]
)