import logging
import os
from datetime import datetime
import io
import base64
from aiogram import Dispatcher, types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery

from bot.keyboards import (
    get_main_keyboard,
    get_cancel_keyboard,
    get_confirm_keyboard
)
from bot.storage import UserData, user_data_storage
from bot.openai_integration import analyze_food_image

# Configure logging
logger = logging.getLogger(__name__)

# States
class CalorieTrackerStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_confirmation = State()
    waiting_for_calorie_limit = State()

# Command handlers
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Initialize user data if not exists
    if user_id not in user_data_storage:
        user_data_storage[user_id] = UserData(user_id)
    
    await state.clear()  # Clear any active states
    
    # Welcome message
    welcome_text = (
        f"👋 Добро пожаловать, {user_name}!\n\n"
        f"Я бот для подсчёта калорий. Вот что я умею:\n"
        f"• Анализировать фото еды и считать калории 📸\n"
        f"• Отслеживать ваше питание в течение дня 📊\n"
        f"• Подсчитывать белки, жиры и углеводы 📝\n"
        f"• Устанавливать персональный лимит калорий ⚙️\n\n"
        f"Нажмите «Сфотографировать еду» чтобы начать!"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🔍 <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ <b>Отправьте фото еды</b> - я проанализирую и посчитаю калории\n"
        "2️⃣ <b>Подтвердите информацию</b> - если всё верно, я добавлю данные в дневник\n"
        "3️⃣ <b>Посмотрите статистику за сегодня</b> - нажмите соответствующую кнопку\n"
        "4️⃣ <b>Установите свой лимит калорий</b> - я буду сообщать, сколько осталось\n\n"
        "<b>Команды:</b>\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n"
        "/today - Показать статистику за сегодня\n"
        "/setlimit - Установить лимит калорий"
    )
    
    await message.answer(help_text, parse_mode="HTML")

async def cmd_today(message: Message):
    """Handle /today command"""
    user_id = message.from_user.id
    
    if user_id not in user_data_storage:
        user_data_storage[user_id] = UserData(user_id)
    
    user_data = user_data_storage[user_id]
    today_stats = user_data.get_today_stats()
    
    if today_stats["entries"] == 0:
        await message.answer(
            "📊 <b>Статистика за сегодня</b>\n\n"
            "У вас пока нет записей за сегодня. Отправьте фото еды, чтобы начать отслеживание.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Calculate remaining calories
    calorie_limit = user_data.calorie_limit
    calories_consumed = today_stats["calories"]
    calories_remaining = max(0, calorie_limit - calories_consumed) if calorie_limit else None
    
    # Prepare the message
    limit_text = f"Лимит калорий: {calorie_limit} ккал\n" if calorie_limit else ""
    remaining_text = f"Осталось: {calories_remaining} ккал\n" if calories_remaining is not None else ""
    over_limit_text = f"Превышение: {abs(calorie_limit - calories_consumed)} ккал\n" if (calorie_limit and calories_consumed > calorie_limit) else ""
    
    stats_text = (
        f"📊 <b>Статистика за {datetime.now().strftime('%d.%m.%Y')}</b>\n\n"
        f"Приёмов пищи: {today_stats['entries']}\n"
        f"{limit_text}"
        f"Потреблено: {calories_consumed} ккал\n"
        f"{remaining_text}"
        f"{over_limit_text}\n"
        f"Белки: {today_stats['protein']}г\n"
        f"Жиры: {today_stats['fat']}г\n"
        f"Углеводы: {today_stats['carbs']}г\n"
    )
    
    await message.answer(stats_text, parse_mode="HTML", reply_markup=get_main_keyboard())

async def cmd_set_limit(message: Message, state: FSMContext):
    """Handle /setlimit command"""
    user_id = message.from_user.id
    
    if user_id not in user_data_storage:
        user_data_storage[user_id] = UserData(user_id)
    
    user_data = user_data_storage[user_id]
    current_limit = user_data.calorie_limit
    
    limit_text = (
        f"⚙️ <b>Установка лимита калорий</b>\n\n"
        f"Текущий лимит: {current_limit if current_limit else 'не установлен'}\n\n"
        f"Введите новый дневной лимит калорий (число):"
    )
    
    await message.answer(limit_text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(CalorieTrackerStates.waiting_for_calorie_limit)

async def process_photo_button(message: Message, state: FSMContext):
    """Handle 'Photo food' button press"""
    await message.answer(
        "📸 Пожалуйста, отправьте фотографию вашей еды, и я проанализирую её калорийность.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CalorieTrackerStates.waiting_for_photo)

async def process_photo(message: Message, state: FSMContext):
    """Process food photo from user"""
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фотографию еды.")
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
        
        if not analysis_result:
            await message.answer(
                "😔 Не удалось распознать еду на фотографии. Пожалуйста, попробуйте сделать более четкое фото.",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
            return
        
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
        await message.bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
        
        # Send results with confirmation buttons
        await message.answer(result_message, parse_mode="HTML", reply_markup=get_confirm_keyboard())
        await state.set_state(CalorieTrackerStates.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.answer(
            "😔 Произошла ошибка при анализе фотографии. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

async def process_confirmation(callback_query: CallbackQuery, state: FSMContext):
    """Process user confirmation of food analysis"""
    user_id = callback_query.from_user.id
    
    # Get analysis data from state
    state_data = await state.get_data()
    analysis = state_data.get("analysis")
    
    if not analysis:
        await callback_query.message.answer(
            "😔 Произошла ошибка. Пожалуйста, попробуйте снова сфотографировать еду.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        await callback_query.answer()
        return
    
    # Save data to user storage
    if user_id not in user_data_storage:
        user_data_storage[user_id] = UserData(user_id)
    
    user_data = user_data_storage[user_id]
    user_data.add_food_entry(
        food_name=analysis.get('food_name', 'Неизвестное блюдо'),
        calories=analysis.get('calories', 0),
        protein=analysis.get('protein', 0),
        fat=analysis.get('fat', 0),
        carbs=analysis.get('carbs', 0)
    )
    
    # Get updated stats
    today_stats = user_data.get_today_stats()
    calorie_limit = user_data.calorie_limit
    calories_consumed = today_stats["calories"]
    calories_remaining = max(0, calorie_limit - calories_consumed) if calorie_limit else None
    
    # Prepare confirmation message
    limit_text = f"Лимит калорий: {calorie_limit} ккал\n" if calorie_limit else ""
    remaining_text = f"Осталось: {calories_remaining} ккал\n" if calories_remaining is not None else ""
    over_limit_text = f"⚠️ <b>Внимание!</b> Вы превысили дневной лимит на {abs(calorie_limit - calories_consumed)} ккал\n" if (calorie_limit and calories_consumed > calorie_limit) else ""
    
    confirm_text = (
        f"✅ <b>Запись добавлена в дневник!</b>\n\n"
        f"📊 <b>Статистика за сегодня:</b>\n"
        f"Приёмов пищи: {today_stats['entries']}\n"
        f"{limit_text}"
        f"Потреблено: {calories_consumed} ккал\n"
        f"{remaining_text}"
        f"{over_limit_text}\n"
        f"Белки: {today_stats['protein']}г\n"
        f"Жиры: {today_stats['fat']}г\n"
        f"Углеводы: {today_stats['carbs']}г\n"
    )
    
    await callback_query.message.answer(confirm_text, parse_mode="HTML", reply_markup=get_main_keyboard())
    await state.clear()
    await callback_query.answer()

async def process_cancel(callback_query: CallbackQuery, state: FSMContext):
    """Cancel current operation"""
    await state.clear()
    await callback_query.message.answer(
        "❌ Операция отменена. Что будем делать дальше?",
        reply_markup=get_main_keyboard()
    )
    await callback_query.answer()

async def process_cancel_button(message: Message, state: FSMContext):
    """Handle cancel button press"""
    await state.clear()
    await message.answer(
        "❌ Операция отменена. Что будем делать дальше?",
        reply_markup=get_main_keyboard()
    )

async def process_calorie_limit(message: Message, state: FSMContext):
    """Process calorie limit setting"""
    try:
        limit = int(message.text.strip())
        if limit <= 0:
            raise ValueError("Limit must be positive")
        
        user_id = message.from_user.id
        
        if user_id not in user_data_storage:
            user_data_storage[user_id] = UserData(user_id)
        
        user_data = user_data_storage[user_id]
        user_data.set_calorie_limit(limit)
        
        await message.answer(
            f"✅ Ваш дневной лимит калорий установлен: <b>{limit} ккал</b>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число для лимита калорий (целое положительное число).",
            reply_markup=get_cancel_keyboard()
        )

def register_handlers(dp: Dispatcher):
    """Register all handlers"""
    # Create a router
    router = Router()
    
    # Command handlers
    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_help, Command("help"))
    router.message.register(cmd_today, Command("today"))
    router.message.register(cmd_set_limit, Command("setlimit"))
    
    # Button handlers
    router.message.register(cmd_today, F.text == "📊 Статистика за сегодня")
    router.message.register(process_photo_button, F.text == "📸 Сфотографировать еду")
    router.message.register(cmd_set_limit, F.text == "⚙️ Установить лимит калорий")
    router.message.register(process_cancel_button, F.text == "❌ Отмена")
    
    # State handlers
    router.message.register(process_photo, F.photo, StateFilter(CalorieTrackerStates.waiting_for_photo))
    router.message.register(process_calorie_limit, StateFilter(CalorieTrackerStates.waiting_for_calorie_limit))
    
    # Callback query handlers
    router.callback_query.register(process_confirmation, F.data == "confirm", StateFilter(CalorieTrackerStates.waiting_for_confirmation))
    router.callback_query.register(process_cancel, F.data == "cancel")
    
    # Include the router in the dispatcher
    dp.include_router(router)
