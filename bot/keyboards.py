from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta
from bot.storage import AVAILABLE_TIMEZONES

def get_main_keyboard():
    """Return the main keyboard with permanent functionality buttons"""
    kb = [
        [
            KeyboardButton(text="📊 Сводка питания"),
            KeyboardButton(text="🍽️ Приемы пищи")
        ],
        [
            KeyboardButton(text="🏠 Главное меню"),
            KeyboardButton(text="⚙️ Настройки")
        ]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, persistent=True)
    return keyboard

def get_confirm_keyboard():
    """Return inline keyboard with confirm/cancel buttons"""
    kb = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def get_stats_keyboard(current_date=None):
    """Return inline keyboard for nutrition stats with date navigation"""
    if current_date is None:
        current_date = date.today()
    
    prev_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
    current_str = current_date.strftime("%d.%m.%Y")
    
    kb = [
        [
            InlineKeyboardButton(text="◀️ Пред. день", callback_data=f"date:{prev_date}"),
            InlineKeyboardButton(text=f"{current_str}", callback_data="current_date"),
            InlineKeyboardButton(text="След. день ▶️", callback_data=f"date:{next_date}")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_stats")
        ]
    ]
    
    # Если текущий день - не сегодня, добавляем кнопку "Сегодня"
    if current_date != date.today():
        today = date.today().strftime("%Y-%m-%d")
        kb.append([InlineKeyboardButton(text="📅 Перейти к сегодня", callback_data=f"date:{today}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def get_meals_keyboard(meals, page=0, page_size=5):
    """Return inline keyboard with meal list and pagination"""
    kb = []
    
    # Добавляем кнопки для каждого приема пищи на текущей странице
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(meals))
    
    for i in range(start_idx, end_idx):
        meal = meals[i]
        meal_name = meal["food_name"]
        meal_calories = meal["calories"]
        kb.append([
            InlineKeyboardButton(
                text=f"{meal_name} ({meal_calories} ккал)",
                callback_data=f"meal_info:{i}"
            )
        ])
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Пред.", callback_data=f"meals_page:{page-1}"))
    
    if end_idx < len(meals):
        nav_buttons.append(InlineKeyboardButton(text="След. ▶️", callback_data=f"meals_page:{page+1}"))
    
    if nav_buttons:
        kb.append(nav_buttons)
    
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_meals")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def get_meal_detail_keyboard(meal_index):
    """Return inline keyboard for detailed meal view"""
    kb = [
        [
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_meal:{meal_index}"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_meals")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def get_settings_keyboard():
    """Return inline keyboard for settings"""
    kb = [
        [
            InlineKeyboardButton(text="🎯 Установить лимит калорий", callback_data="set_calorie_limit")
        ],
        [
            InlineKeyboardButton(text="🕒 Изменить часовой пояс", callback_data="set_timezone")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="back_to_main")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def get_timezone_keyboard(current_timezone="МСК", page=0):
    """Return inline keyboard with timezone options"""
    # Разбиваем часовые пояса на страницы
    page_size = 7
    timezone_items = list(AVAILABLE_TIMEZONES.items())
    total_pages = (len(timezone_items) - 1) // page_size + 1
    
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(timezone_items))
    
    kb = []
    
    # Добавляем заголовок с текущим часовым поясом
    for i in range(start_idx, end_idx):
        tz_code, tz_name = timezone_items[i]
        # Добавляем маркер текущего часового пояса
        prefix = "✓ " if tz_code == current_timezone else ""
        kb.append([
            InlineKeyboardButton(
                text=f"{prefix}{tz_code} ({tz_name.split('/')[-1]})",
                callback_data=f"timezone:{tz_code}"
            )
        ])
    
    # Добавляем навигацию
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Пред.", callback_data=f"timezone_page:{page-1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="След. ▶️", callback_data=f"timezone_page:{page+1}"))
    
    if nav_buttons:
        kb.append(nav_buttons)
    
    # Добавляем кнопку назад
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def get_main_menu_inline_keyboard():
    """Return inline keyboard for main menu"""
    kb = [
        [
            InlineKeyboardButton(text="📊 Сводка питания", callback_data="show_stats")
        ],
        [
            InlineKeyboardButton(text="🍽️ Приемы пищи", callback_data="show_meals")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard
