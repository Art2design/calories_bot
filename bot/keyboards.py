from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta, datetime
from bot.storage import AVAILABLE_TIMEZONES

def get_main_keyboard():
    """Return the main keyboard with permanent functionality buttons"""
    kb = [
        [
            KeyboardButton(text="📊 Сводка питания"),
            KeyboardButton(text="🍽️ Приемы пищи")
        ],
        [
            KeyboardButton(text="⚙️ Настройки"),
            KeyboardButton(text="ℹ️ Инструкция")
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
    elif isinstance(current_date, str):
        # Если дата передана как строка, преобразуем её в объект date
        try:
            current_date = datetime.strptime(current_date, "%Y-%m-%d").date()
        except ValueError:
            current_date = date.today()
    
    # Получаем сегодняшнюю дату для сравнения
    today = date.today()
    current_str = current_date.strftime("%d.%m.%Y")
    
    # Кнопки навигации
    nav_row = []
    
    # Добавляем кнопку предыдущего дня
    prev_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
    nav_row.append(InlineKeyboardButton(text="◀️ Пред.", callback_data=f"date:{prev_date}"))
    
    # Добавляем текущую дату
    nav_row.append(InlineKeyboardButton(text=f"{current_str}", callback_data="refresh_stats"))
    
    # Добавляем кнопку следующего дня
    next_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
    if current_date < today:
        nav_row.append(InlineKeyboardButton(text="След. ▶️", callback_data=f"date:{next_date}"))
    
    kb = [nav_row]
    
    # Добавляем кнопки управления
    buttons_row = [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_stats")]
    kb.append(buttons_row)
    
    # Если текущий день - не сегодня, добавляем кнопку "Сегодня"
    if current_date != today:
        today_str = today.strftime("%Y-%m-%d")
        kb.append([InlineKeyboardButton(text="📅 Перейти к сегодня", callback_data=f"date:{today_str}")])
    
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
    
    # Добавляем кнопку обновления
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
            InlineKeyboardButton(text="📊 Установить КБЖУ", callback_data="set_kbju")
        ],
        [
            InlineKeyboardButton(text="⚖️ Указать вес и % жира", callback_data="set_body_metrics")
        ],
        [
            InlineKeyboardButton(text="🕒 Изменить часовой пояс", callback_data="set_timezone")
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

# Функция get_main_menu_inline_keyboard удалена по запросу пользователя

def get_kbju_format_keyboard():
    """Return keyboard with format selection for KBJU limits"""
    kb = [
        [
            InlineKeyboardButton(text="✍️ Ввести вручную", callback_data="kbju_manual")
        ],
        [
            InlineKeyboardButton(text="🧮 Рассчитать по весу", callback_data="kbju_calculate")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def get_improved_stats_keyboard(stats, width=8):
    """Return inline keyboard for improved stats display with all nutrients"""
    
    # Кнопки для перехода к подробной статистике по нутриентам
    kb = [
        [
            InlineKeyboardButton(text="📊 Все нутриенты", callback_data="all_nutrients")
        ]
    ]
    
    # Навигация по датам (используем существующую функцию)
    date_keyboard = get_stats_keyboard(stats.get("date"))
    
    # Объединяем клавиатуры
    for row in date_keyboard.inline_keyboard:
        kb.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_all_nutrients_keyboard(stats):
    """Return keyboard with detailed information about all nutrients"""
    kb = [
        [
            InlineKeyboardButton(text="🔙 Вернуться к статистике", callback_data="back_to_stats")
        ]
    ]
    
    # Добавляем кнопки для навигации по датам
    date_keyboard = get_stats_keyboard(stats.get("date"))
    for row in date_keyboard.inline_keyboard:
        kb.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_macros_settings_keyboard():
    """Return keyboard for macros settings with additional nutrients"""
    kb = [
        [
            InlineKeyboardButton(text="💪 Белки", callback_data="set_protein")
        ],
        [
            InlineKeyboardButton(text="🍗 Жиры", callback_data="set_fat")
        ],
        [
            InlineKeyboardButton(text="🍚 Углеводы", callback_data="set_carbs")
        ],
        [
            InlineKeyboardButton(text="🥗 Клетчатка", callback_data="set_fiber")
        ],
        [
            InlineKeyboardButton(text="🍬 Сахар", callback_data="set_sugar")
        ],
        [
            InlineKeyboardButton(text="🧂 Натрий", callback_data="set_sodium")
        ],
        [
            InlineKeyboardButton(text="🥚 Холестерин", callback_data="set_cholesterol")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
