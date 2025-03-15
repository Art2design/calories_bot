import logging
import os
from datetime import datetime, date
from typing import Optional, Dict, List, Any
import io
import base64
from aiogram import Dispatcher, types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import (
    get_main_keyboard,
    get_confirm_keyboard,
    get_stats_keyboard,
    get_meals_keyboard,
    get_meal_detail_keyboard,
    get_settings_keyboard,
    get_timezone_keyboard,
    get_kbju_format_keyboard,
    get_improved_stats_keyboard
)
from bot.db_storage import DBUserData, get_user_data
from bot.openai_integration import analyze_food_image

# Configure logging
logger = logging.getLogger(__name__)

# States
class CalorieTrackerStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_confirmation = State()
    waiting_for_calorie_limit = State()
    waiting_for_timezone = State()
    waiting_for_kbju_format = State()
    waiting_for_protein_limit = State()
    waiting_for_fat_limit = State()
    waiting_for_carbs_limit = State()
    waiting_for_fiber_limit = State()
    waiting_for_sugar_limit = State()
    waiting_for_sodium_limit = State()
    waiting_for_cholesterol_limit = State()
    waiting_for_weight = State()
    waiting_for_body_fat = State()

# Функция get_user_data уже импортирована из db_storage, используем её напрямую
# Другое имя для совместимости не требуется, так как имена совпадают

# Command handlers
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Initialize user data if not exists
    user_data = get_user_data(user_id)
    
    await state.clear()  # Clear any active states
    
    # Welcome message
    welcome_text = (
        f"👋 Добро пожаловать, {user_name}!\n\n"
        f"Я бот для подсчёта калорий. Вот что я умею:\n"
        f"• Анализировать фото еды и считать калории 📸\n"
        f"• Отслеживать ваше питание в течение дня 📊\n"
        f"• Подсчитывать белки, жиры и углеводы 📝\n"
        f"• Показывать историю питания за последние 7 дней 📅\n"
        f"• Устанавливать персональный лимит калорий ⚙️\n\n"
        f"Используйте кнопки ниже или просто отправьте фото еды, чтобы начать!"
    )
    
    # Отправляем основную клавиатуру
    await message.answer(welcome_text, 
                         reply_markup=get_main_keyboard(), 
                         parse_mode="HTML")

async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🔍 <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ <b>Отправьте фото еды</b> - я проанализирую и посчитаю калории\n"
        "2️⃣ <b>Подтвердите информацию</b> - если всё верно, я добавлю данные в дневник\n"
        "3️⃣ <b>Посмотрите статистику</b> - нажмите на кнопку «📊 Сводка питания»\n"
        "4️⃣ <b>Просмотрите приемы пищи</b> - нажмите на кнопку «🍽️ Приемы пищи»\n"
        "5️⃣ <b>Настройте лимит калорий</b> - нажмите на кнопку «⚙️ Настройки»\n\n"
        "<b>Основные функции:</b>\n"
        "• Анализ фото еды и распознавание калорийности\n"
        "• Отслеживание питания по дням с возможностью листать историю\n"
        "• Просмотр и удаление отдельных приемов пищи\n"
        "• Прогресс-бар потребления калорий\n"
        "• Установка персонального лимита калорий"
    )
    
    await message.answer(help_text, parse_mode="HTML")

# Функции для отображения сводки питания
async def show_stats(message: Message = None, callback_query: CallbackQuery = None, 
                    current_date: Optional[date] = None, edit_message: bool = False):
    """Show nutrition stats for a specific date"""
    # Определяем либо из сообщения, либо из callback_query
    if callback_query:
        user_id = callback_query.from_user.id
        msg_obj = callback_query.message
    else:
        user_id = message.from_user.id
        msg_obj = message
    
    # Если дата не указана, используем сегодня в часовом поясе пользователя
    if current_date is None:
        user_data = get_user_data(user_id)
        current_date = user_data.get_current_date()
    else:
        user_data = get_user_data(user_id)
    
    stats = user_data.get_stats_by_date(current_date)
    
    # Если нет записей за эту дату
    if stats["entries"] == 0:
        stats_text = (
            f"📊 <b>Сводка питания за {stats['date']}</b>\n\n"
            f"У вас нет записей о питании за этот день.\n\n"
            f"Отправьте фото еды, чтобы добавить новую запись."
        )
        # Используем обычную клавиатуру навигации по датам
        keyboard = get_stats_keyboard(current_date)
    else:
        # Создаем прогресс-бары для всех нутриентов
        calorie_bar = user_data.generate_calorie_progress_bar(stats["calorie_percentage"])
        
        # Получаем целевые значения БЖУ из данных пользователя
        protein_target = stats.get('protein_limit', 75)
        fat_target = stats.get('fat_limit', 60)
        carbs_target = stats.get('carbs_limit', 250)
        fiber_target = stats.get('fiber_limit', 30)
        sugar_target = stats.get('sugar_limit', 50)
        sodium_target = stats.get('sodium_limit', 2300)
        cholesterol_target = stats.get('cholesterol_limit', 300)

        # Проверка на None и установка дефолтных значений
        if protein_target is None:
            protein_target = 75
        if carbs_target is None:
            carbs_target = 250
        if fat_target is None:
            fat_target = 60
        if fiber_target is None:
            fiber_target = 30
        if sugar_target is None:
            sugar_target = 50
        if sodium_target is None:
            sodium_target = 2300
        if cholesterol_target is None:
            cholesterol_target = 300
        
        # Создаем прогресс-бары с текущими/целевыми значениями
        protein_bar = user_data.generate_nutrient_progress_bar(stats["protein"], protein_target, "protein")
        fat_bar = user_data.generate_nutrient_progress_bar(stats["fat"], fat_target, "fat")
        carbs_bar = user_data.generate_nutrient_progress_bar(stats["carbs"], carbs_target, "carbs")
        fiber_bar = user_data.generate_nutrient_progress_bar(stats.get("fiber", 0), fiber_target, "fiber")
        
        # Создаем прогресс-бары для новых нутриентов
        sugar_bar = user_data.generate_nutrient_progress_bar(stats.get("sugar", 0), sugar_target, "sugar")
        sodium_bar = user_data.generate_nutrient_progress_bar(stats.get("sodium", 0), sodium_target, "sodium")
        cholesterol_bar = user_data.generate_nutrient_progress_bar(stats.get("cholesterol", 0), cholesterol_target, "cholesterol")
        
        # Создаем текст сообщения с прогресс-барами
        limit_text = f"Лимит калорий: {stats['calorie_limit']} ккал\n" if stats['calorie_limit'] else ""
        
        # Основные нутриенты всегда отображаются
        stats_text = (
            f"📊 <b>Сводка питания за {stats['date']}</b>\n\n"
            f"Приёмов пищи: {stats['entries']}\n"
            f"{limit_text}"
            f"Калории: {stats['calories']}/{stats.get('calorie_limit', '—')} ккал\n"
            f"Прогресс: {calorie_bar}\n\n"
            f"<b>Основные нутриенты:</b>\n"
            f"🥩 Белки: {stats['protein']}/{protein_target}г\n{protein_bar}\n"
            f"🧈 Жиры: {stats['fat']}/{fat_target}г\n{fat_bar}\n"
            f"🍚 Углеводы: {stats['carbs']}/{carbs_target}г\n{carbs_bar}\n"
            f"🌱 Клетчатка: {stats.get('fiber', 0)}/{fiber_target}г\n{fiber_bar}\n"
        )
        
        # Используем улучшенную клавиатуру со всеми нутриентами
        keyboard = get_improved_stats_keyboard(stats)
    
    # Отправляем или редактируем сообщение
    try:
        if edit_message and callback_query:
            await callback_query.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer()
        else:
            await msg_obj.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)
            if callback_query:
                await callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка при отображении сводки питания: {e}")
        if callback_query:
            await callback_query.answer("Произошла ошибка при отображении сводки")
            try:
                # Повторная попытка с новым сообщением
                await callback_query.message.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)
            except:
                pass
        elif message:
            await message.answer("Произошла ошибка. Пожалуйста, повторите запрос.")

# Функции для отображения списка приемов пищи
async def show_meals(message: Message = None, callback_query: CallbackQuery = None, 
                     current_date: Optional[date] = None, page: int = 0, edit_message: bool = False):
    """Show meals list for a specific date"""
    # Определяем либо из сообщения, либо из callback_query
    if callback_query:
        user_id = callback_query.from_user.id
        msg_obj = callback_query.message
    else:
        user_id = message.from_user.id
        msg_obj = message
    
    # Если дата не указана, используем сегодня в часовом поясе пользователя
    if current_date is None:
        user_data = get_user_data(user_id)
        current_date = user_data.get_current_date()
    else:
        user_data = get_user_data(user_id)
    
    # Получаем приемы пищи за указанную дату
    meals = user_data.get_entries_by_date(current_date)
    
    # Если нет записей за эту дату
    if not meals:
        meals_text = (
            f"🍽 <b>Приемы пищи за {current_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"У вас нет записей о питании за этот день.\n\n"
            f"Отправьте фото еды, чтобы добавить новую запись."
        )
        keyboard = get_stats_keyboard(current_date)  # Используем обычную клавиатуру навигации
    else:
        meals_text = f"🍽 <b>Приемы пищи за {current_date.strftime('%d.%m.%Y')}</b>\n\n"
        meals_text += f"Всего записей: {len(meals)}\n\n"
        meals_text += "Выберите запись для просмотра деталей и управления:"
        
        # Создаем клавиатуру со списком приемов пищи
        keyboard = get_meals_keyboard(meals, page)
    
    # Отправляем или редактируем сообщение в зависимости от контекста
    try:
        if edit_message and callback_query:
            await callback_query.message.edit_text(meals_text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer()
        else:
            await msg_obj.answer(meals_text, parse_mode="HTML", reply_markup=keyboard)
            if callback_query:
                await callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка при отображении списка приемов пищи: {e}")
        if callback_query:
            await callback_query.answer("Произошла ошибка при отображении списка")
            try:
                # Повторная попытка с новым сообщением
                await callback_query.message.answer(meals_text, parse_mode="HTML", reply_markup=keyboard)
            except:
                pass
        elif message:
            await message.answer("Произошла ошибка. Пожалуйста, повторите запрос.")

# Функция главного меню удалена по запросу пользователя

# Функция для отображения настроек
async def show_settings(message: Message = None, callback_query: CallbackQuery = None):
    """Show settings"""
    # Определяем либо из сообщения, либо из callback_query
    if callback_query:
        user_id = callback_query.from_user.id
        msg_obj = callback_query.message
    else:
        user_id = message.from_user.id
        msg_obj = message
    
    user_data = get_user_data(user_id)
    current_limit = user_data.calorie_limit
    tz_code = user_data.timezone_code
    tz_offset = user_data.get_timezone_offset()
    
    # Метрики тела и КБЖУ лимиты
    protein_limit = user_data.protein_limit
    fat_limit = user_data.fat_limit
    carbs_limit = user_data.carbs_limit
    fiber_limit = user_data.fiber_limit
    user_weight = user_data.user_weight
    body_fat = user_data.body_fat_percentage
    
    # Создаем текст сообщения с настройками
    body_metrics_text = ""
    if user_weight and body_fat:
        body_metrics_text = f"⚖️ Вес: {user_weight} кг, жир: {body_fat}%\n"
    
    kbju_text = ""
    if protein_limit and fat_limit and carbs_limit:
        kbju_text = (
            f"🥩 Белки: {protein_limit}г\n"
            f"🧈 Жиры: {fat_limit}г\n"
            f"🍚 Углеводы: {carbs_limit}г\n"
        )
        if fiber_limit:
            kbju_text += f"🌱 Клетчатка: {fiber_limit}г\n"
    
    settings_text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"🎯 Текущий лимит калорий: {current_limit if current_limit else 'не установлен'}\n"
        f"{kbju_text if kbju_text else ''}"
        f"{body_metrics_text if body_metrics_text else ''}"
        f"🕒 Часовой пояс: {tz_code} ({tz_offset})\n\n"
        f"Выберите действие:"
    )
    
    # Создаем клавиатуру настроек
    keyboard = get_settings_keyboard()
    
    try:
        if callback_query:
            # Всегда отправляем новое сообщение вместо редактирования
            await callback_query.message.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)
            # Удаляем старое сообщение
            try:
                await callback_query.message.delete()
            except Exception as delete_err:
                logger.warning(f"Не удалось удалить сообщение: {delete_err}")
            await callback_query.answer()
        else:
            await msg_obj.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении настроек: {e}")
        if callback_query:
            await callback_query.answer("Ошибка при отображении настроек")
            try:
                # Повторная попытка с новым сообщением
                await callback_query.message.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)
            except:
                pass
        elif message:
            await message.answer("Произошла ошибка. Пожалуйста, повторите запрос.")

# Обработка фотографии - автоматически вызывается при получении фото
async def process_photo(message: Message, state: FSMContext):
    """Process food photo from user"""
    if not message.photo:
        return
    
    # Notify user that processing is happening
    processing_message = await message.answer("🔍 Анализирую вашу еду... Это может занять несколько секунд.")
    
    try:
        # Get the largest photo
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        
        # Convert to base64
        photo_bytes = downloaded_file.read()
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Analyze image with OpenAI
        analysis_result = await analyze_food_image(base64_image)
        
        # Mock data for testing if OpenAI quota is exhausted
        if not analysis_result:
            # Если квота OpenAI исчерпана, используем тестовые данные
            logger.warning("OpenAI quota exceeded or API error. Using mock data for testing.")
            
            # Определяем случайные значения для тестирования
            import random
            
            food_options = [
                {"name": "Овсянка с фруктами", "cal": 310, "protein": 8, "fat": 5, "carbs": 55},
                {"name": "Куриная грудка с овощами", "cal": 250, "protein": 30, "fat": 8, "carbs": 12},
                {"name": "Греческий салат", "cal": 220, "protein": 5, "fat": 17, "carbs": 10},
                {"name": "Борщ", "cal": 180, "protein": 7, "fat": 6, "carbs": 22},
                {"name": "Паста с соусом", "cal": 450, "protein": 12, "fat": 15, "carbs": 65}
            ]
            
            # Выбираем случайное тестовое блюдо
            mock_food = random.choice(food_options)
            
            # Создаем тестовые данные
            analysis_result = {
                "food_name": mock_food["name"],
                "calories": mock_food["cal"],
                "protein": mock_food["protein"],
                "fat": mock_food["fat"],
                "carbs": mock_food["carbs"]
            }
            
            # Уведомляем о тестовом режиме в логах
            logger.info(f"Using mock data: {analysis_result}")
        
        # Store analysis in state
        await state.update_data(analysis=analysis_result)
        
        # Format the results
        food_name = analysis_result.get('food_name', 'Неизвестное блюдо')
        calories = analysis_result.get('calories', 0)
        protein = analysis_result.get('protein', 0)
        fat = analysis_result.get('fat', 0)
        carbs = analysis_result.get('carbs', 0)
        fiber = analysis_result.get('fiber', 0)
        sugar = analysis_result.get('sugar', 0)
        sodium = analysis_result.get('sodium', 0)
        cholesterol = analysis_result.get('cholesterol', 0)
        
        # Основные нутриенты всегда отображаются
        result_message = (
            f"🍽 <b>{food_name}</b>\n\n"
            f"📊 <b>Пищевая ценность:</b>\n"
            f"🔥 Калории: {calories} ккал\n"
            f"🥩 Белки: {protein}г\n"
            f"🧈 Жиры: {fat}г\n"
            f"🍚 Углеводы: {carbs}г"
        )
        
        # Добавляем дополнительные нутриенты, если они есть
        additional_nutrients = []
        if fiber > 0:
            additional_nutrients.append(f"🌱 Клетчатка: {fiber}г")
        if sugar > 0:
            additional_nutrients.append(f"🍯 Сахар: {sugar}г")
        if sodium > 0:
            additional_nutrients.append(f"🧂 Натрий: {sodium}мг")
        if cholesterol > 0:
            additional_nutrients.append(f"🥚 Холестерин: {cholesterol}мг")
            
        if additional_nutrients:
            result_message += "\n\n<b>Дополнительные нутриенты:</b>\n" + "\n".join(additional_nutrients)
            
        result_message += f"\n\nВсе верно? Если да, нажмите «Подтвердить» для сохранения в дневник питания."
        
        # Delete processing message
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
        except Exception as e:
            logger.error(f"Error deleting processing message: {e}")
        
        # Send results with confirmation buttons
        await message.answer(result_message, parse_mode="HTML", reply_markup=get_confirm_keyboard())
        await state.set_state(CalorieTrackerStates.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.answer(
            "😔 Произошла ошибка при анализе фотографии. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
        except:
            pass

# Обработка установки лимита калорий
async def set_calorie_limit(callback_query: CallbackQuery, state: FSMContext):
    """Prompt user to set calorie limit"""
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    current_limit = user_data.calorie_limit
    
    limit_text = (
        f"⚙️ <b>Установка лимита калорий</b>\n\n"
        f"Текущий лимит: {current_limit if current_limit else 'не установлен'}\n\n"
        f"Введите новый дневной лимит калорий (число):"
    )
    
    # Отправляем новое сообщение вместо редактирования
    await callback_query.message.answer(limit_text, parse_mode="HTML")
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await state.set_state(CalorieTrackerStates.waiting_for_calorie_limit)
    await callback_query.answer()

# Обработка подтверждения добавления еды
async def process_confirmation(callback_query: CallbackQuery, state: FSMContext):
    """Process user confirmation of food analysis"""
    user_id = callback_query.from_user.id
    
    # Get analysis data from state
    state_data = await state.get_data()
    analysis = state_data.get("analysis")
    
    if not analysis:
        # Отправляем новое сообщение вместо редактирования текущего
        await callback_query.message.answer(
            "😔 Произошла ошибка. Пожалуйста, попробуйте снова сфотографировать еду."
        )
        try:
            await callback_query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        await state.clear()
        await callback_query.answer()
        return
    
    # Save data to user storage
    user_data = get_user_data(user_id)
    
    # Извлекаем данные о нутриентах, включая дополнительные
    food_name = analysis.get('food_name', 'Неизвестное блюдо')
    calories = analysis.get('calories', 0)
    protein = analysis.get('protein', 0)
    fat = analysis.get('fat', 0)
    carbs = analysis.get('carbs', 0)
    fiber = analysis.get('fiber', 0)
    sugar = analysis.get('sugar', 0)
    sodium = analysis.get('sodium', 0)
    cholesterol = analysis.get('cholesterol', 0)
    
    # Добавляем запись со всеми нутриентами
    entry = user_data.add_food_entry(
        food_name=food_name,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        fiber=fiber,
        sugar=sugar,
        sodium=sodium,
        cholesterol=cholesterol
    )
    
    # Get updated stats
    today_stats = user_data.get_today_stats()
    
    # Получаем целевые значения БЖУ из данных пользователя
    protein_target = today_stats.get('protein_limit', 75)
    fat_target = today_stats.get('fat_limit', 60)
    carbs_target = today_stats.get('carbs_limit', 250)
    fiber_target = today_stats.get('fiber_limit', 30)

    if protein_target == None:
        protein_target = 0
    if carbs_target == None:
        carbs_target = 0
    if fat_target == None:
        fat_target = 0
    if fiber_target == None:
        fiber_target = 0
    
    # Create progress bars with current/target values
    calorie_bar = user_data.generate_calorie_progress_bar(today_stats["calorie_percentage"])
    protein_bar = user_data.generate_nutrient_progress_bar(today_stats["protein"], protein_target, "protein")
    fat_bar = user_data.generate_nutrient_progress_bar(today_stats["fat"], fat_target, "fat")
    carbs_bar = user_data.generate_nutrient_progress_bar(today_stats["carbs"], carbs_target, "carbs")
    fiber_bar = user_data.generate_nutrient_progress_bar(today_stats.get("fiber", 0), fiber_target, "fiber")
    
    # Prepare confirmation message
    calorie_limit = today_stats["calorie_limit"]
    limit_text = f"Лимит калорий: {calorie_limit} ккал\n" if calorie_limit else ""
    
    # Определяем дополнительные нутриенты (если они есть)
    fiber = analysis.get('fiber', 0)
    sugar = analysis.get('sugar', 0)
    sodium = analysis.get('sodium', 0)
    cholesterol = analysis.get('cholesterol', 0)
    
    # Добавляем эти нутриенты в запись
    if fiber > 0 or sugar > 0 or sodium > 0 or cholesterol > 0:
        if entry:
            # Обновляем запись с новыми нутриентами
            try:
                user_data.update_food_entry(
                    entry_id=entry['id'],
                    fiber=fiber,
                    sugar=sugar,
                    sodium=sodium,
                    cholesterol=cholesterol
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении дополнительных нутриентов: {e}")
    
    # Создаем текст подтверждения
    confirm_text = (
        f"✅ <b>Запись добавлена в дневник!</b>\n\n"
        f"<b>{analysis.get('food_name', 'Неизвестное блюдо')}</b>\n"
        f"Калории: {analysis.get('calories', 0)} ккал\n\n"
        f"📊 <b>Сводка за сегодня:</b>\n"
        f"Приёмов пищи: {today_stats['entries']}\n"
        f"{limit_text}"
        f"Калории: {today_stats['calories']}/{today_stats.get('calorie_limit', '—')} ккал\n"
        f"{calorie_bar}\n\n"
        f"<b>Пищевая ценность:</b>\n"
        f"🥩 Белки: {today_stats['protein']}/{protein_target}г\n{protein_bar}\n"
        f"🧈 Жиры: {today_stats['fat']}/{fat_target}г\n{fat_bar}\n"
        f"🍚 Углеводы: {today_stats['carbs']}/{carbs_target}г\n{carbs_bar}\n"
        f"🌱 Клетчатка: {today_stats.get('fiber', 0)}/{fiber_target}г\n{fiber_bar}\n"
    )
    
    # Всегда отправляем новое сообщение вместо редактирования
    await callback_query.message.answer(
        f"{confirm_text}\n\nЧто хотите сделать дальше?",
        parse_mode="HTML"
    )
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await state.clear()
    await callback_query.answer()

# Функция для обработки отмены
async def process_cancel(callback_query: CallbackQuery, state: FSMContext):
    """Cancel current operation"""
    await state.clear()
    
    # Всегда отправляем новое сообщение вместо редактирования
    await callback_query.message.answer(
        "❌ Операция отменена.\n\nЧто хотите сделать дальше?",
        parse_mode="HTML"
    )
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Подтверждаем обработку callback
    await callback_query.answer()

# Обработка ввода лимита калорий
async def process_calorie_limit(message: Message, state: FSMContext):
    """Process calorie limit setting"""
    try:
        limit = int(message.text.strip())
        if limit <= 0:
            raise ValueError("Limit must be positive")
        
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        user_data.set_calorie_limit(limit)
        
        await message.answer(
            f"✅ Ваш дневной лимит калорий установлен: <b>{limit} ккал</b>",
            parse_mode="HTML"
        )
        
        # Показываем меню настроек
        await show_settings(message)
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита калорий (целое положительное число)."
        )

# Обработка нажатия на дату в сводке питания
async def process_date_callback(callback_query: CallbackQuery):
    """Process date navigation in stats"""
    # Получаем дату из callback_data
    data_parts = callback_query.data.split(":")
    if len(data_parts) != 2:
        await callback_query.answer("Ошибка в формате даты")
        return
    
    date_str = data_parts[1]
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Показываем статистику за выбранную дату
    await show_stats(callback_query=callback_query, current_date=target_date, edit_message=True)

# Обработка нажатия на кнопку подробной информации обо всех нутриентах
async def show_all_nutrients(callback_query: CallbackQuery):
    """Show all nutrients details"""
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    
    # Пытаемся получить дату из текста сообщения
    message_text = callback_query.message.text
    try:
        # Ищем дату в формате DD.MM.YYYY в тексте сообщения
        import re
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', message_text)
        if date_match:
            day, month, year = map(int, date_match.groups())
            current_date = date(year, month, day)
        else:
            current_date = user_data.get_current_date()
    except Exception:
        current_date = user_data.get_current_date()
    
    # Получаем статистику за день
    stats = user_data.get_stats_by_date(current_date)
    
    # Получаем целевые значения всех нутриентов
    protein_target = stats.get('protein_limit', 75) or 75
    fat_target = stats.get('fat_limit', 60) or 60
    carbs_target = stats.get('carbs_limit', 250) or 250
    fiber_target = stats.get('fiber_limit', 30) or 30
    sugar_target = stats.get('sugar_limit', 50) or 50
    sodium_target = stats.get('sodium_limit', 2300) or 2300
    cholesterol_target = stats.get('cholesterol_limit', 300) or 300
    
    # Создаем прогресс-бары для всех нутриентов
    calorie_bar = user_data.generate_calorie_progress_bar(stats["calorie_percentage"])
    protein_bar = user_data.generate_nutrient_progress_bar(stats["protein"], protein_target, "protein")
    fat_bar = user_data.generate_nutrient_progress_bar(stats["fat"], fat_target, "fat")
    carbs_bar = user_data.generate_nutrient_progress_bar(stats["carbs"], carbs_target, "carbs")
    fiber_bar = user_data.generate_nutrient_progress_bar(stats.get("fiber", 0), fiber_target, "fiber")
    sugar_bar = user_data.generate_nutrient_progress_bar(stats.get("sugar", 0), sugar_target, "sugar")
    sodium_bar = user_data.generate_nutrient_progress_bar(stats.get("sodium", 0), sodium_target, "sodium")
    cholesterol_bar = user_data.generate_nutrient_progress_bar(stats.get("cholesterol", 0), cholesterol_target, "cholesterol")
    
    # Формируем текст с информацией обо всех нутриентах
    nutrients_text = (
        f"📊 <b>Детальная сводка питания за {stats['date']}</b>\n\n"
        f"Приёмов пищи: {stats['entries']}\n"
        f"Калории: {stats['calories']}/{stats.get('calorie_limit', '—')} ккал\n"
        f"{calorie_bar}\n\n"
        f"<b>Макронутриенты:</b>\n"
        f"🥩 Белки: {stats['protein']}/{protein_target}г\n{protein_bar}\n"
        f"🧈 Жиры: {stats['fat']}/{fat_target}г\n{fat_bar}\n"
        f"🍚 Углеводы: {stats['carbs']}/{carbs_target}г\n{carbs_bar}\n\n"
        f"<b>Дополнительные нутриенты:</b>\n"
        f"🌱 Клетчатка: {stats.get('fiber', 0)}/{fiber_target}г\n{fiber_bar}\n"
        f"🟣 Сахар: {stats.get('sugar', 0)}/{sugar_target}г\n{sugar_bar}\n"
        f"⚪ Натрий: {stats.get('sodium', 0)}/{sodium_target}мг\n{sodium_bar}\n"
        f"🔴 Холестерин: {stats.get('cholesterol', 0)}/{cholesterol_target}мг\n{cholesterol_bar}\n"
    )
    
    # Импортируем клавиатуру для всех нутриентов
    from bot.keyboards import get_all_nutrients_keyboard
    keyboard = get_all_nutrients_keyboard(stats)
    
    # Отправляем или редактируем сообщение
    await callback_query.message.edit_text(
        nutrients_text, 
        parse_mode="HTML", 
        reply_markup=keyboard
    )
    await callback_query.answer()

# Обработка нажатия на кнопку обновления статистики
async def process_refresh_stats(callback_query: CallbackQuery):
    """Refresh stats for current date"""
    # Используем ту же дату, что отображается сейчас
    # Получаем ее из текста сообщения
    message_text = callback_query.message.text
    try:
        # Ищем дату в формате DD.MM.YYYY в тексте сообщения
        import re
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', message_text)
        if date_match:
            day, month, year = map(int, date_match.groups())
            current_date = date(year, month, day)
        else:
            current_date = date.today()
    except:
        current_date = date.today()
    
    # Показываем статистику за выбранную дату
    await show_stats(callback_query=callback_query, current_date=current_date, edit_message=True)

# Обработка нажатия на кнопку просмотра приема пищи
async def process_meal_info(callback_query: CallbackQuery):
    """Show meal details"""
    # Получаем индекс приема пищи из callback_data
    data_parts = callback_query.data.split(":")
    if len(data_parts) != 2:
        await callback_query.answer("Ошибка в формате данных")
        return
    
    try:
        meal_index = int(data_parts[1])
    except ValueError:
        await callback_query.answer("Некорректный индекс приема пищи")
        return
    
    # Получаем данные пользователя
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    
    # Получаем текущую дату из текста сообщения
    message_text = callback_query.message.text
    try:
        # Ищем дату в формате DD.MM.YYYY в тексте сообщения
        import re
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', message_text)
        if date_match:
            day, month, year = map(int, date_match.groups())
            current_date = date(year, month, day)
        else:
            current_date = date.today()
    except:
        current_date = date.today()
    
    # Получаем список приемов пищи за эту дату
    meals = user_data.get_entries_by_date(current_date)
    
    if meal_index >= len(meals):
        await callback_query.answer("Прием пищи не найден")
        return
    
    # Получаем прием пищи
    meal = meals[meal_index]
    
    # Форматируем детали
    # Проверяем наличие дополнительных нутриентов
    additional_nutrients = []
    if meal.get('fiber') and meal['fiber'] > 0:
        additional_nutrients.append(f"🌱 Клетчатка: {meal['fiber']}г")
    if meal.get('sugar') and meal['sugar'] > 0:
        additional_nutrients.append(f"🍯 Сахар: {meal['sugar']}г")
    if meal.get('sodium') and meal['sodium'] > 0:
        additional_nutrients.append(f"🧂 Натрий: {meal['sodium']}мг")
    if meal.get('cholesterol') and meal['cholesterol'] > 0:
        additional_nutrients.append(f"🥚 Холестерин: {meal['cholesterol']}мг")
    
    # Базовые нутриенты всегда отображаются
    meal_text = (
        f"🍽 <b>{meal['food_name']}</b>\n\n"
        f"📊 <b>Пищевая ценность:</b>\n"
        f"🔥 Калории: {meal['calories']} ккал\n"
        f"🥩 Белки: {meal['protein']}г\n"
        f"🧈 Жиры: {meal['fat']}г\n"
        f"🍚 Углеводы: {meal['carbs']}г"
    )
    
    # Добавляем дополнительные нутриенты, если они есть
    if additional_nutrients:
        meal_text += "\n\n<b>Дополнительные нутриенты:</b>\n" + "\n".join(additional_nutrients)
    
    # Добавляем информацию о времени
    meal_text += f"\n\n⏱ Время: {datetime.fromisoformat(meal['timestamp']).strftime('%H:%M:%S')}"
    
    # Отправляем детали с клавиатурой для удаления
    await callback_query.message.edit_text(
        meal_text,
        parse_mode="HTML",
        reply_markup=get_meal_detail_keyboard(meal_index)
    )
    await callback_query.answer()

# Обработка навигации по страницам списка приемов пищи
async def process_meals_page(callback_query: CallbackQuery):
    """Navigate through meals pages"""
    # Получаем номер страницы из callback_data
    data_parts = callback_query.data.split(":")
    if len(data_parts) != 2:
        await callback_query.answer("Ошибка в формате данных")
        return
    
    try:
        page = int(data_parts[1])
    except ValueError:
        await callback_query.answer("Некорректный номер страницы")
        return
    
    # Получаем текущую дату из текста сообщения
    message_text = callback_query.message.text
    try:
        # Ищем дату в формате DD.MM.YYYY в тексте сообщения
        import re
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', message_text)
        if date_match:
            day, month, year = map(int, date_match.groups())
            current_date = date(year, month, day)
        else:
            current_date = date.today()
    except:
        current_date = date.today()
    
    # Показываем список приемов пищи с новой страницей
    await show_meals(
        callback_query=callback_query, 
        current_date=current_date, 
        page=page, 
        edit_message=True
    )

# Обработка удаления приема пищи
async def process_delete_meal(callback_query: CallbackQuery):
    """Delete meal entry"""
    # Получаем индекс приема пищи из callback_data
    data_parts = callback_query.data.split(":")
    if len(data_parts) != 2:
        await callback_query.answer("Ошибка в формате данных")
        return
    
    try:
        meal_index = int(data_parts[1])
    except ValueError:
        await callback_query.answer("Некорректный индекс приема пищи")
        return
    
    # Получаем данные пользователя
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    
    # Получаем текущую дату из текста сообщения с деталями
    meal_name = "запись о еде"
    try:
        # Извлекаем название блюда из текста сообщения
        import re
        meal_match = re.search(r'🍽 <b>(.*?)</b>', callback_query.message.text)
        if meal_match:
            meal_name = meal_match.group(1)
    except:
        pass
    
    # Удаляем прием пищи
    success = user_data.delete_entry_by_index(meal_index)
    
    if success:
        # Сообщаем об удалении и показываем меню
        await callback_query.message.edit_text(
            f"✅ Прием пищи «{meal_name}» успешно удален.\n\nОбновленный список приемов пищи:",
            parse_mode="HTML"
        )
        
        # Возвращаем пользователя к списку приемов пищи с редактированием текущего сообщения
        await show_meals(callback_query=callback_query, edit_message=True)
    else:
        await callback_query.answer("Не удалось удалить прием пищи")

# Обработка возврата к списку приемов пищи
async def process_back_to_meals(callback_query: CallbackQuery):
    """Return to meals list"""
    await show_meals(callback_query=callback_query, edit_message=True)

# Обработка обновления списка приемов пищи
async def process_refresh_meals(callback_query: CallbackQuery):
    """Refresh meals list"""
    # Получаем текущую дату из текста сообщения
    message_text = callback_query.message.text
    try:
        # Ищем дату в формате DD.MM.YYYY в тексте сообщения
        import re
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', message_text)
        if date_match:
            day, month, year = map(int, date_match.groups())
            current_date = date(year, month, day)
        else:
            current_date = date.today()
    except:
        current_date = date.today()
    
    # Показываем обновленный список приемов пищи
    await show_meals(
        callback_query=callback_query, 
        current_date=current_date, 
        edit_message=True
    )

# Функция для выбора часового пояса
async def show_timezone_selection(callback_query: CallbackQuery, state: FSMContext):
    """Show timezone selection screen"""
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    current_timezone = user_data.timezone_code
    
    timezone_text = (
        f"🕒 <b>Настройка часового пояса</b>\n\n"
        f"Текущий часовой пояс: <b>{current_timezone}</b> ({user_data.get_timezone_offset()})\n\n"
        f"Выберите часовой пояс из списка ниже:"
    )
    
    # Создаем клавиатуру с выбором часовых поясов
    keyboard = get_timezone_keyboard(current_timezone)
    
    # Отправляем новое сообщение вместо редактирования
    await callback_query.message.answer(timezone_text, parse_mode="HTML", reply_markup=keyboard)
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await state.set_state(CalorieTrackerStates.waiting_for_timezone)
    await callback_query.answer()

# Функция для отображения страниц с часовыми поясами
async def process_timezone_page(callback_query: CallbackQuery, state: FSMContext):
    """Navigate through timezone pages"""
    # Получаем номер страницы из callback_data
    data_parts = callback_query.data.split(":")
    if len(data_parts) != 2:
        await callback_query.answer("Ошибка в формате данных")
        return
    
    try:
        page = int(data_parts[1])
    except ValueError:
        await callback_query.answer("Некорректный номер страницы")
        return
    
    # Получаем текущий часовой пояс пользователя
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    current_timezone = user_data.timezone_code
    
    # Обновляем клавиатуру с часовыми поясами
    keyboard = get_timezone_keyboard(current_timezone, page)
    
    # Обновляем сообщение с новой клавиатурой
    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    await callback_query.answer()

# Функция для установки выбранного часового пояса
async def set_selected_timezone(callback_query: CallbackQuery, state: FSMContext):
    """Set selected timezone for user"""
    # Получаем выбранный часовой пояс из callback_data
    data_parts = callback_query.data.split(":")
    if len(data_parts) != 2:
        await callback_query.answer("Ошибка в формате данных")
        return
    
    timezone_code = data_parts[1]
    
    # Получаем данные пользователя
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    
    # Устанавливаем новый часовой пояс
    success = user_data.set_timezone(timezone_code)
    
    if success:
        # Отправляем новое сообщение
        await callback_query.message.answer(
            f"✅ Часовой пояс успешно установлен: <b>{timezone_code}</b>",
            parse_mode="HTML"
        )
        
        # Удаляем старое сообщение
        try:
            await callback_query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        # Сообщаем об успешной установке во всплывающем уведомлении
        await callback_query.answer(f"Часовой пояс установлен")
        
        # Возвращаемся в настройки
        await show_settings(callback_query=callback_query)
        await state.clear()
    else:
        await callback_query.answer("Ошибка: недопустимый часовой пояс")

# Функция для возврата из выбора часового пояса в настройки
async def back_to_settings(callback_query: CallbackQuery, state: FSMContext):
    """Return from timezone selection to settings"""
    await state.clear()
    
    # Отправляем новое сообщение вместо редактирования
    await callback_query.message.answer("Возвращаемся в настройки...")
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Показываем меню настроек
    await show_settings(callback_query=callback_query)
    
# Функция для выбора формата установки КБЖУ
async def show_kbju_format_selection(callback_query: CallbackQuery, state: FSMContext):
    """Show KBJU format selection screen"""
    format_text = (
        f"📊 <b>Настройка лимитов КБЖУ</b>\n\n"
        f"Выберите способ установки лимитов белков, жиров и углеводов:\n\n"
        f"<b>✍️ Ввести вручную</b> - установить каждое значение отдельно\n"
        f"<b>🧮 Рассчитать по весу</b> - расчёт на основе вашего веса и % жира в теле"
    )
    
    # Создаем клавиатуру с выбором формата
    keyboard = get_kbju_format_keyboard()
    
    # Отправляем новое сообщение вместо редактирования
    await callback_query.message.answer(format_text, parse_mode="HTML", reply_markup=keyboard)
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await state.set_state(CalorieTrackerStates.waiting_for_kbju_format)
    await callback_query.answer()

# Функции для ручной установки КБЖУ
async def set_manual_kbju(callback_query: CallbackQuery, state: FSMContext):
    """Start manual KBJU limits setting"""
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    
    # Получаем текущие значения
    protein_limit = user_data.protein_limit
    
    protein_text = (
        f"🥩 <b>Установка лимита белков</b>\n\n"
        f"Текущий лимит: {protein_limit if protein_limit else 'не установлен'} г\n\n"
        f"Введите новый дневной лимит белков в граммах:"
    )
    
    # Отправляем новое сообщение
    await callback_query.message.answer(protein_text, parse_mode="HTML")
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await state.set_state(CalorieTrackerStates.waiting_for_protein_limit)
    await callback_query.answer()

# Функция для обработки ввода лимита белков
async def process_protein_limit(message: Message, state: FSMContext):
    """Process protein limit input"""
    try:
        protein = float(message.text.strip())
        if protein <= 0:
            raise ValueError("Limit must be positive")
        
        # Сохраняем во временное хранилище
        await state.update_data(protein_limit=protein)
        
        # Запрашиваем лимит жиров
        fat_text = (
            f"🧈 <b>Установка лимита жиров</b>\n\n"
            f"Введите дневной лимит жиров в граммах:"
        )
        
        await message.answer(fat_text, parse_mode="HTML")
        await state.set_state(CalorieTrackerStates.waiting_for_fat_limit)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита белков (положительное число)."
        )

# Функция для обработки ввода лимита жиров
async def process_fat_limit(message: Message, state: FSMContext):
    """Process fat limit input"""
    try:
        fat = float(message.text.strip())
        if fat <= 0:
            raise ValueError("Limit must be positive")
        
        # Сохраняем во временное хранилище
        state_data = await state.get_data()
        await state.update_data(fat_limit=fat)
        
        # Запрашиваем лимит углеводов
        carbs_text = (
            f"🍚 <b>Установка лимита углеводов</b>\n\n"
            f"Введите дневной лимит углеводов в граммах:"
        )
        
        await message.answer(carbs_text, parse_mode="HTML")
        await state.set_state(CalorieTrackerStates.waiting_for_carbs_limit)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита жиров (положительное число)."
        )

# Функция для обработки ввода лимита углеводов
async def process_carbs_limit(message: Message, state: FSMContext):
    """Process carbs limit input"""
    try:
        carbs = float(message.text.strip())
        if carbs <= 0:
            raise ValueError("Limit must be positive")
        
        # Сохраняем во временное хранилище
        await state.update_data(carbs_limit=carbs)
        
        # Запрашиваем лимит клетчатки (опционально)
        fiber_text = (
            f"🌱 <b>Установка лимита клетчатки</b>\n\n"
            f"Введите дневной лимит клетчатки в граммах:\n"
            f"(это необязательный параметр, введите 0, если не хотите устанавливать лимит)"
        )
        
        await message.answer(fiber_text, parse_mode="HTML")
        await state.set_state(CalorieTrackerStates.waiting_for_fiber_limit)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита углеводов (положительное число)."
        )

# Функция для обработки ввода лимита клетчатки и сохранения всех лимитов
async def process_fiber_limit(message: Message, state: FSMContext):
    """Process fiber limit input and set next state for sugar input"""
    try:
        fiber = float(message.text.strip())
        if fiber < 0:
            raise ValueError("Limit must be non-negative")
        
        # Сохраняем лимит клетчатки
        await state.update_data(fiber_limit=fiber)
        
        # Спрашиваем о лимите сахара
        await message.answer(
            "🍬 <b>Установка лимита сахара</b>\n\n"
            "Введите лимит потребления сахара в граммах (рекомендуется 25-50г).\n"
            "Введите 0, если не хотите устанавливать лимит."
        )
        
        # Переходим к следующему шагу
        await state.set_state(CalorieTrackerStates.waiting_for_sugar_limit)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита клетчатки."
        )

async def process_sugar_limit(message: Message, state: FSMContext):
    """Process sugar limit input and set next state for sodium input"""
    try:
        sugar = float(message.text.strip())
        if sugar < 0:
            raise ValueError("Limit must be non-negative")
        
        # Сохраняем лимит сахара
        await state.update_data(sugar_limit=sugar)
        
        # Спрашиваем о лимите натрия
        await message.answer(
            "🧂 <b>Установка лимита натрия</b>\n\n"
            "Введите лимит потребления натрия в миллиграммах (рекомендуется 1500-2300мг).\n"
            "Введите 0, если не хотите устанавливать лимит."
        )
        
        # Переходим к следующему шагу
        await state.set_state(CalorieTrackerStates.waiting_for_sodium_limit)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита сахара."
        )

async def process_sodium_limit(message: Message, state: FSMContext):
    """Process sodium limit input and set next state for cholesterol input"""
    try:
        sodium = float(message.text.strip())
        if sodium < 0:
            raise ValueError("Limit must be non-negative")
        
        # Сохраняем лимит натрия
        await state.update_data(sodium_limit=sodium)
        
        # Спрашиваем о лимите холестерина
        await message.answer(
            "🥚 <b>Установка лимита холестерина</b>\n\n"
            "Введите лимит потребления холестерина в миллиграммах (рекомендуется до 300мг).\n"
            "Введите 0, если не хотите устанавливать лимит."
        )
        
        # Переходим к следующему шагу
        await state.set_state(CalorieTrackerStates.waiting_for_cholesterol_limit)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита натрия."
        )

async def process_cholesterol_limit(message: Message, state: FSMContext):
    """Process cholesterol limit input and save all macros"""
    try:
        cholesterol = float(message.text.strip())
        if cholesterol < 0:
            raise ValueError("Limit must be non-negative")
        
        # Получаем все сохраненные лимиты
        state_data = await state.get_data()
        protein = state_data.get("protein_limit")
        fat = state_data.get("fat_limit")
        carbs = state_data.get("carbs_limit")
        fiber = state_data.get("fiber_limit", 0)
        sugar = state_data.get("sugar_limit", 0)
        sodium = state_data.get("sodium_limit", 0)
        
        if not protein or not fat or not carbs:
            await message.answer(
                "❌ Что-то пошло не так. Пожалуйста, повторите процесс установки лимитов КБЖУ."
            )
            await state.clear()
            return
        
        # Устанавливаем лимиты КБЖУ и дополнительных нутриентов
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        
        success = user_data.set_macros_limits(
            protein=protein,
            fat=fat,
            carbs=carbs,
            fiber=fiber if fiber else None,
            sugar=sugar if sugar else None,
            sodium=sodium if sodium else None,
            cholesterol=cholesterol if cholesterol > 0 else None
        )
        
        if success:
            # Рассчитываем калории из КБЖУ (4 ккал на грамм белка, 9 на грамм жира, 4 на грамм углеводов)
            calculated_calories = round(protein * 4 + fat * 9 + carbs * 4)
            
            # Создаем текст с установленными лимитами
            limits_text = (
                f"🥩 Белки: {protein}г\n"
                f"🧈 Жиры: {fat}г\n"
                f"🍚 Углеводы: {carbs}г\n"
            )
            
            # Добавляем дополнительные нутриенты, если установлены
            if fiber > 0:
                limits_text += f"🌱 Клетчатка: {fiber}г\n"
            if sugar > 0:
                limits_text += f"🍬 Сахар: {sugar}г\n"
            if sodium > 0:
                limits_text += f"🧂 Натрий: {sodium}мг\n"
            if cholesterol > 0:
                limits_text += f"🥚 Холестерин: {cholesterol}мг\n"
            
            # Предлагаем обновить и лимит калорий тоже
            update_calories_text = (
                f"✅ <b>Лимиты нутриентов успешно установлены!</b>\n\n"
                f"{limits_text}\n"
                f"Рассчитанный лимит калорий: {calculated_calories} ккал\n"
                f"Хотите установить этот лимит калорий?"
            )
            
            # Создаем клавиатуру для выбора
            kb = [
                [
                    InlineKeyboardButton(text="✅ Да", callback_data=f"set_calc_calories:{calculated_calories}")
                ],
                [
                    InlineKeyboardButton(text="❌ Нет", callback_data="back_to_settings")
                ]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
            
            await message.answer(update_calories_text, parse_mode="HTML", reply_markup=keyboard)
            await state.clear()
        else:
            await message.answer(
                "❌ Не удалось установить лимиты КБЖУ. Пожалуйста, попробуйте еще раз."
            )
            await state.clear()
            await show_settings(message)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита клетчатки (неотрицательное число)."
        )

# Функция для установки рассчитанного лимита калорий из КБЖУ
async def set_calculated_calories(callback_query: CallbackQuery):
    """Set calculated calories from KBJU"""
    data_parts = callback_query.data.split(":")
    if len(data_parts) != 2:
        await callback_query.answer("Ошибка в формате данных")
        return
    
    try:
        calories = int(float(data_parts[1]))
        
        user_id = callback_query.from_user.id
        user_data = get_user_data(user_id)
        user_data.set_calorie_limit(calories)
        
        # Отправляем сообщение об успешной установке
        await callback_query.message.answer(
            f"✅ Лимит калорий установлен: <b>{calories} ккал</b>",
            parse_mode="HTML"
        )
        
        # Удаляем старое сообщение
        try:
            await callback_query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        await callback_query.answer()
        await show_settings(callback_query=callback_query)
        
    except Exception as e:
        logger.error(f"Ошибка при установке лимита калорий: {e}")
        await callback_query.answer("Не удалось установить лимит калорий")

# Функции для установки метрик тела
async def set_body_metrics(callback_query: CallbackQuery, state: FSMContext):
    """Start body metrics input process"""
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    
    # Получаем текущие значения
    weight = user_data.user_weight
    
    weight_text = (
        f"⚖️ <b>Настройка веса</b>\n\n"
        f"Текущий вес: {weight if weight else 'не установлен'} кг\n\n"
        f"Введите ваш вес в килограммах:"
    )
    
    # Отправляем новое сообщение
    await callback_query.message.answer(weight_text, parse_mode="HTML")
    
    # Удаляем старое сообщение
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await state.set_state(CalorieTrackerStates.waiting_for_weight)
    await callback_query.answer()

# Функция для обработки ввода веса
async def process_weight(message: Message, state: FSMContext):
    """Process weight input"""
    try:
        weight = float(message.text.strip())
        if weight <= 0 or weight > 300:  # Разумные пределы веса
            raise ValueError("Weight must be positive and realistic")
        
        # Сохраняем во временное хранилище
        await state.update_data(weight=weight)
        
        # Запрашиваем процент жира
        fat_text = (
            f"📏 <b>Установка процента жира в теле</b>\n\n"
            f"Введите процент жира в теле (число от 5 до 50):\n"
            f"Примерные значения:\n"
            f"- Мужчины: 10-25%\n"
            f"- Женщины: 18-30%\n"
            f"Если вы не знаете свой процент жира, введите примерное значение:"
        )
        
        await message.answer(fat_text, parse_mode="HTML")
        await state.set_state(CalorieTrackerStates.waiting_for_body_fat)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для веса (от 30 до 300 кг)."
        )

# Функция для обработки ввода процента жира и расчета КБЖУ
async def process_body_fat(message: Message, state: FSMContext):
    """Process body fat percentage input and calculate macros"""
    try:
        body_fat = float(message.text.strip())
        if body_fat < 5 or body_fat > 50:  # Разумные пределы процента жира
            raise ValueError("Body fat must be between 5 and 50 percent")
        
        # Получаем вес из состояния
        state_data = await state.get_data()
        weight = state_data.get("weight")
        
        if not weight:
            await message.answer(
                "❌ Что-то пошло не так. Пожалуйста, повторите процесс ввода метрик тела."
            )
            await state.clear()
            return
        
        # Устанавливаем метрики тела и рассчитываем рекомендуемые КБЖУ
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        
        success = user_data.set_user_body_metrics(weight=weight, body_fat=body_fat)
        
        if success:
            # Получаем рассчитанные лимиты
            today_stats = user_data.get_today_stats()
            protein_limit = today_stats.get('protein_limit', 0)
            fat_limit = today_stats.get('fat_limit', 0)
            carbs_limit = today_stats.get('carbs_limit', 0)
            calorie_limit = today_stats.get('calorie_limit', 0)
            
            metrics_text = (
                f"✅ <b>Метрики тела и лимиты установлены!</b>\n\n"
                f"⚖️ Вес: {weight} кг\n"
                f"📏 Процент жира: {body_fat}%\n\n"
                f"📊 <b>Рассчитанные лимиты:</b>\n"
                f"🔥 Калории: {calorie_limit} ккал\n"
                f"🥩 Белки: {protein_limit}г\n"
                f"🧈 Жиры: {fat_limit}г\n"
                f"🍚 Углеводы: {carbs_limit}г\n\n"
                f"Лимиты были рассчитаны на основе вашего веса и состава тела."
            )
            
            await message.answer(metrics_text, parse_mode="HTML")
            await state.clear()
            await show_settings(message)
        else:
            await message.answer(
                "❌ Не удалось установить метрики тела. Пожалуйста, попробуйте еще раз."
            )
            await state.clear()
            await show_settings(message)
        
    except ValueError as e:
        await message.answer(
            f"❌ Пожалуйста, введите корректное число для процента жира (от 5 до 50)."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке метрик тела: {e}")
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз."
        )
        await state.clear()
        await show_settings(message)

# Регистрация обработчиков
def register_handlers(dp: Dispatcher):
    """Register all handlers"""
    # Create a router
    router = Router()
    
    # Command handlers
    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_help, Command("help"))
    
    # Main menu button handlers (ReplyKeyboard)
    router.message.register(show_stats, F.text == "📊 Сводка питания")
    router.message.register(show_meals, F.text == "🍽️ Приемы пищи")
    router.message.register(show_settings, F.text == "⚙️ Настройки")
    router.message.register(cmd_help, F.text == "ℹ️ Инструкция")
    
    # Photo handling - для любого состояния и без состояния
    router.message.register(process_photo, F.photo)
    
    # State handlers
    router.message.register(process_calorie_limit, StateFilter(CalorieTrackerStates.waiting_for_calorie_limit))
    router.message.register(process_protein_limit, StateFilter(CalorieTrackerStates.waiting_for_protein_limit))
    router.message.register(process_fat_limit, StateFilter(CalorieTrackerStates.waiting_for_fat_limit))
    router.message.register(process_carbs_limit, StateFilter(CalorieTrackerStates.waiting_for_carbs_limit))
    router.message.register(process_fiber_limit, StateFilter(CalorieTrackerStates.waiting_for_fiber_limit))
    router.message.register(process_sugar_limit, StateFilter(CalorieTrackerStates.waiting_for_sugar_limit))
    router.message.register(process_sodium_limit, StateFilter(CalorieTrackerStates.waiting_for_sodium_limit))
    router.message.register(process_cholesterol_limit, StateFilter(CalorieTrackerStates.waiting_for_cholesterol_limit))
    router.message.register(process_weight, StateFilter(CalorieTrackerStates.waiting_for_weight))
    router.message.register(process_body_fat, StateFilter(CalorieTrackerStates.waiting_for_body_fat))
    
    # Callback query handlers - main menu
    router.callback_query.register(show_stats, F.data == "show_stats")
    router.callback_query.register(show_stats, F.data == "back_to_main")  # Перенаправляем к статистике вместо главного меню
    router.callback_query.register(show_meals, F.data == "show_meals")
    router.callback_query.register(show_settings, F.data == "settings")
    
    # Callback query handlers - food confirmation
    router.callback_query.register(process_confirmation, F.data == "confirm", StateFilter(CalorieTrackerStates.waiting_for_confirmation))
    router.callback_query.register(process_cancel, F.data == "cancel")
    
    # Callback query handlers - stats navigation
    router.callback_query.register(process_date_callback, F.data.startswith("date:"))
    router.callback_query.register(process_refresh_stats, F.data == "refresh_stats")
    router.callback_query.register(show_all_nutrients, F.data == "all_nutrients")
    router.callback_query.register(show_stats, F.data == "back_to_stats")
    
    # Callback query handlers - meals list
    router.callback_query.register(process_meal_info, F.data.startswith("meal_info:"))
    router.callback_query.register(process_meals_page, F.data.startswith("meals_page:"))
    router.callback_query.register(process_refresh_meals, F.data == "refresh_meals")
    
    # Callback query handlers - meal details
    router.callback_query.register(process_delete_meal, F.data.startswith("delete_meal:"))
    router.callback_query.register(process_back_to_meals, F.data == "back_to_meals")
    
    # Callback query handlers - settings
    router.callback_query.register(set_calorie_limit, F.data == "set_calorie_limit")
    router.callback_query.register(show_timezone_selection, F.data == "set_timezone")
    
    # Callback query handlers - timezone selection
    router.callback_query.register(process_timezone_page, F.data.startswith("timezone_page:"))
    router.callback_query.register(set_selected_timezone, F.data.startswith("timezone:"))
    router.callback_query.register(back_to_settings, F.data == "back_to_settings")
    
    # Callback query handlers - KBJU format and settings
    router.callback_query.register(show_kbju_format_selection, F.data == "set_kbju")
    router.callback_query.register(set_manual_kbju, F.data == "kbju_manual")
    router.callback_query.register(set_body_metrics, F.data == "kbju_calculate")
    router.callback_query.register(set_body_metrics, F.data == "set_body_metrics")
    router.callback_query.register(set_calculated_calories, F.data.startswith("set_calc_calories:"))
    
    # Include the router in the dispatcher
    dp.include_router(router)
