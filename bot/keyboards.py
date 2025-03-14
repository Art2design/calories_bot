from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """Return the main keyboard with basic functionality"""
    # В aiogram 3.x используем builder паттерн для конструирования клавиатуры
    kb = [
        [
            KeyboardButton(text="📸 Сфотографировать еду"),
            KeyboardButton(text="📊 Статистика за сегодня")
        ],
        [
            KeyboardButton(text="⚙️ Установить лимит калорий")
        ]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    return keyboard

def get_cancel_keyboard():
    """Return keyboard with cancel button"""
    kb = [[KeyboardButton(text="❌ Отмена")]]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    return keyboard

def get_confirm_keyboard():
    """Return inline keyboard with confirm/cancel buttons"""
    # В aiogram 3.x также используем builder паттерн для inline клавиатур
    kb = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard
