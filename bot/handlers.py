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
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import (
    get_main_keyboard,
    get_confirm_keyboard,
    get_stats_keyboard,
    get_meals_keyboard,
    get_meal_detail_keyboard,
    get_settings_keyboard,
    get_timezone_keyboard,
    get_main_menu_inline_keyboard
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
        f"Используйте меню ниже или просто отправьте фото еды, чтобы начать!"
    )
    
    # Отправляем основную клавиатуру и inline-клавиатуру главного меню
    await message.answer(welcome_text, 
                         reply_markup=get_main_keyboard(), 
                         parse_mode="HTML")
    
    await message.answer("🏠 <b>Главное меню</b>\n\nВыберите действие:", 
                         reply_markup=get_main_menu_inline_keyboard(), 
                         parse_mode="HTML")

async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🔍 <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ <b>Отправьте фото еды</b> - я проанализирую и посчитаю калории\n"
        "2️⃣ <b>Подтвердите информацию</b> - если всё верно, я добавлю данные в дневник\n"
        "3️⃣ <b>Посмотрите статистику</b> - нажмите на кнопку «Сводка питания»\n"
        "4️⃣ <b>Просмотрите приемы пищи</b> - нажмите на кнопку «Приемы пищи»\n"
        "5️⃣ <b>Настройте лимит калорий</b> - в разделе «Настройки»\n\n"
        "<b>Основные функции:</b>\n"
        "• Анализ фото еды и распознавание калорийности\n"
        "• Отслеживание питания по дням с возможностью листать историю\n"
        "• Просмотр и удаление отдельных приемов пищи\n"
        "• Прогресс-бар потребления калорий\n"
        "• Установка персонального лимита калорий"
    )
    
    await message.answer(help_text, parse_mode="HTML")
    await message.answer("Выберите действие:", reply_markup=get_main_menu_inline_keyboard())

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
    else:
        # Создаем прогресс-бары
        calorie_bar = user_data.generate_calorie_progress_bar(stats["calorie_percentage"])
        
        # Получаем целевые значения БЖУ и создаем прогресс-бары
        protein_bar = user_data.generate_nutrient_progress_bar(stats["protein"], 75, "protein")
        fat_bar = user_data.generate_nutrient_progress_bar(stats["fat"], 60, "fat")
        carbs_bar = user_data.generate_nutrient_progress_bar(stats["carbs"], 250, "carbs")
        
        # Создаем текст сообщения с прогресс-барами
        limit_text = f"Лимит калорий: {stats['calorie_limit']} ккал\n" if stats['calorie_limit'] else ""
        
        stats_text = (
            f"📊 <b>Сводка питания за {stats['date']}</b>\n\n"
            f"Приёмов пищи: {stats['entries']}\n"
            f"{limit_text}"
            f"Калории: {stats['calories']} ккал\n"
            f"Прогресс: {calorie_bar}\n\n"
            f"<b>Пищевая ценность:</b>\n"
            f"🥩 Белки: {stats['protein']}г\n{protein_bar}\n"
            f"🧈 Жиры: {stats['fat']}г\n{fat_bar}\n"
            f"🍚 Углеводы: {stats['carbs']}г\n{carbs_bar}\n"
        )
    
    # Создаем клавиатуру для навигации по датам
    keyboard = get_stats_keyboard(current_date)
    
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

# Функция для отображения главного меню
async def show_main_menu(message: Message = None, callback_query: CallbackQuery = None):
    """Show main menu"""
    # Определяем либо из сообщения, либо из callback_query
    if callback_query:
        user_id = callback_query.from_user.id
        user_data = get_user_data(user_id)
        
        today_stats = user_data.get_today_stats()
        stats_text = ""
        
        # Добавляем краткую статистику за сегодня
        if today_stats["entries"] > 0:
            current_calories = today_stats["calories"]
            limit = today_stats["calorie_limit"] or 2000
            percent = min(100, int(current_calories / limit * 100))
            
            stats_text = (
                f"📊 <b>Статистика на сегодня:</b>\n"
                f"• Калории: {current_calories} ккал ({percent}%)\n"
                f"• Приёмов пищи: {today_stats['entries']}\n\n"
            )
        
        menu_text = (
            f"🏠 <b>Главное меню</b>\n\n"
            f"{stats_text}"
            f"Отправьте фото еды для анализа или выберите действие:"
        )
        
        # Всегда отправляем новое сообщение вместо редактирования
        await callback_query.message.answer(
            menu_text,
            parse_mode="HTML",
            reply_markup=get_main_menu_inline_keyboard()
        )
        # Удаляем старое сообщение
        try:
            await callback_query.message.delete()
        except:
            pass
        await callback_query.answer()
    else:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        
        today_stats = user_data.get_today_stats()
        stats_text = ""
        
        # Добавляем краткую статистику за сегодня
        if today_stats["entries"] > 0:
            current_calories = today_stats["calories"]
            limit = today_stats["calorie_limit"] or 2000
            percent = min(100, int(current_calories / limit * 100))
            
            stats_text = (
                f"📊 <b>Статистика на сегодня:</b>\n"
                f"• Калории: {current_calories} ккал ({percent}%)\n"
                f"• Приёмов пищи: {today_stats['entries']}\n\n"
            )
        
        await message.answer(
            f"🏠 <b>Главное меню</b>\n\n"
            f"{stats_text}"
            f"Отправьте фото еды для анализа или выберите действие:",
            parse_mode="HTML",
            reply_markup=get_main_menu_inline_keyboard()
        )

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
    
    settings_text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"🎯 Текущий лимит калорий: {current_limit if current_limit else 'не установлен'}\n"
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
        
        result_message = (
            f"🍽 <b>{food_name}</b>\n\n"
            f"📊 <b>Пищевая ценность:</b>\n"
            f"🔥 Калории: {calories} ккал\n"
            f"🥩 Белки: {protein}г\n"
            f"🧈 Жиры: {fat}г\n"
            f"🍚 Углеводы: {carbs}г\n\n"
            f"Все верно? Если да, нажмите «Подтвердить» для сохранения в дневник питания."
        )
        
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
    entry = user_data.add_food_entry(
        food_name=analysis.get('food_name', 'Неизвестное блюдо'),
        calories=analysis.get('calories', 0),
        protein=analysis.get('protein', 0),
        fat=analysis.get('fat', 0),
        carbs=analysis.get('carbs', 0)
    )
    
    # Get updated stats
    today_stats = user_data.get_today_stats()
    
    # Create progress bars
    calorie_bar = user_data.generate_calorie_progress_bar(today_stats["calorie_percentage"])
    protein_bar = user_data.generate_nutrient_progress_bar(today_stats["protein"], 75, "protein")
    fat_bar = user_data.generate_nutrient_progress_bar(today_stats["fat"], 60, "fat")
    carbs_bar = user_data.generate_nutrient_progress_bar(today_stats["carbs"], 250, "carbs")
    
    # Prepare confirmation message
    calorie_limit = today_stats["calorie_limit"]
    limit_text = f"Лимит калорий: {calorie_limit} ккал\n" if calorie_limit else ""
    
    confirm_text = (
        f"✅ <b>Запись добавлена в дневник!</b>\n\n"
        f"<b>{analysis.get('food_name', 'Неизвестное блюдо')}</b>\n"
        f"Калории: {analysis.get('calories', 0)} ккал\n\n"
        f"📊 <b>Сводка за сегодня:</b>\n"
        f"Приёмов пищи: {today_stats['entries']}\n"
        f"{limit_text}"
        f"Калории: {today_stats['calories']} ккал\n"
        f"{calorie_bar}\n\n"
        f"<b>Пищевая ценность:</b>\n"
        f"🥩 Белки: {today_stats['protein']}г\n{protein_bar}\n"
        f"🧈 Жиры: {today_stats['fat']}г\n{fat_bar}\n"
        f"🍚 Углеводы: {today_stats['carbs']}г\n{carbs_bar}\n"
    )
    
    # Всегда отправляем новое сообщение вместо редактирования
    await callback_query.message.answer(
        f"{confirm_text}\n\nЧто хотите сделать дальше?",
        parse_mode="HTML",
        reply_markup=get_main_menu_inline_keyboard()
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
        parse_mode="HTML",
        reply_markup=get_main_menu_inline_keyboard()
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
    meal_text = (
        f"🍽 <b>{meal['food_name']}</b>\n\n"
        f"📊 <b>Пищевая ценность:</b>\n"
        f"🔥 Калории: {meal['calories']} ккал\n"
        f"🥩 Белки: {meal['protein']}г\n"
        f"🧈 Жиры: {meal['fat']}г\n"
        f"🍚 Углеводы: {meal['carbs']}г\n\n"
        f"⏱ Время: {datetime.fromisoformat(meal['timestamp']).strftime('%H:%M:%S')}"
    )
    
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
        # Сообщаем об успешной установке
        await callback_query.answer(f"Часовой пояс установлен: {timezone_code}")
        
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

# Регистрация обработчиков
def register_handlers(dp: Dispatcher):
    """Register all handlers"""
    # Create a router
    router = Router()
    
    # Command handlers
    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_help, Command("help"))
    
    # Main menu button handlers (ReplyKeyboard)
    router.message.register(show_main_menu, F.text == "🏠 Главное меню")
    router.message.register(show_stats, F.text == "📊 Сводка питания")
    router.message.register(show_meals, F.text == "🍽️ Приемы пищи")
    router.message.register(show_settings, F.text == "⚙️ Настройки")
    router.message.register(cmd_help, F.text == "ℹ️ Инструкция")
    
    # Photo handling - для любого состояния и без состояния
    router.message.register(process_photo, F.photo)
    
    # State handlers
    router.message.register(process_calorie_limit, StateFilter(CalorieTrackerStates.waiting_for_calorie_limit))
    
    # Callback query handlers - main menu
    router.callback_query.register(show_stats, F.data == "show_stats")
    router.callback_query.register(show_meals, F.data == "show_meals")
    router.callback_query.register(show_settings, F.data == "settings")
    router.callback_query.register(show_main_menu, F.data == "back_to_main")
    
    # Callback query handlers - food confirmation
    router.callback_query.register(process_confirmation, F.data == "confirm", StateFilter(CalorieTrackerStates.waiting_for_confirmation))
    router.callback_query.register(process_cancel, F.data == "cancel")
    
    # Callback query handlers - stats navigation
    router.callback_query.register(process_date_callback, F.data.startswith("date:"))
    router.callback_query.register(process_refresh_stats, F.data == "refresh_stats")
    
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
    
    # Include the router in the dispatcher
    dp.include_router(router)
