import logging
import os
import pytz
from datetime import datetime, date, tzinfo, timedelta
from typing import Dict, List, Any, Optional

from bot.models import User, FoodEntry, get_db, init_db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_

# Настройка логирования
logger = logging.getLogger(__name__)

# Доступные часовые пояса
AVAILABLE_TIMEZONES = {
    "МСК": "Europe/Moscow",       # Москва UTC+3
    "UTC": "UTC",                 # Всемирное координированное время UTC+0
    "CET": "Europe/Paris",        # Центральноевропейское время UTC+1
    "EET": "Europe/Kiev",         # Восточноевропейское время UTC+2
    "GMT": "Etc/GMT",             # Среднее время по Гринвичу UTC+0
    "EKAT": "Asia/Yekaterinburg", # Екатеринбург UTC+5
    "NOVS": "Asia/Novosibirsk",   # Новосибирск UTC+7
    "IRKT": "Asia/Irkutsk",       # Иркутск UTC+8
    "VLAD": "Asia/Vladivostok",   # Владивосток UTC+10
    "MAGA": "Asia/Magadan",       # Магадан UTC+11
    "PET": "Asia/Kamchatka",      # Петропавловск-Камчатский UTC+12
    "SAMT": "Europe/Samara",      # Самара UTC+4
    "KRAT": "Asia/Krasnoyarsk",   # Красноярск UTC+7
    "YEKT": "Asia/Yekaterinburg", # Екатеринбург UTC+5
    "OMST": "Asia/Omsk",          # Омск UTC+6
    "BAKU": "Asia/Baku",          # Баку UTC+4
    "TBIL": "Asia/Tbilisi",       # Тбилиси UTC+4
    "YREV": "Asia/Yerevan",       # Ереван UTC+4
    "MINS": "Europe/Minsk",       # Минск UTC+3
    "KIEV": "Europe/Kiev",        # Киев UTC+2
}

class DBUserData:
    """Класс для работы с данными пользователя в базе данных"""
    
    def __init__(self, user_id: int):
        """Инициализация данных пользователя, загрузка из базы или создание новой записи"""
        self.user_id = user_id
        self.calorie_limit = None
        self.timezone_code = "МСК"
        self.load_from_db()
    
    def load_from_db(self):
        """Загрузить данные пользователя из базы"""
        db = get_db()
        try:
            user = db.query(User).filter(User.id == self.user_id).first()
            if user:
                self.calorie_limit = user.calorie_limit
                self.timezone_code = user.timezone_code
            else:
                # Создаем нового пользователя
                user = User(id=self.user_id, timezone_code=self.timezone_code)
                db.add(user)
                db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при загрузке пользователя из БД: {e}")
            db.rollback()
        finally:
            db.close()
    
    @property
    def timezone(self) -> tzinfo:
        """Получить объект часового пояса пользователя"""
        tz_name = AVAILABLE_TIMEZONES.get(self.timezone_code, "Europe/Moscow")
        return pytz.timezone(tz_name)
    
    def get_current_datetime(self) -> datetime:
        """Получить текущее время в часовом поясе пользователя"""
        # Используем timezone как свойство
        tz = self.timezone
        return datetime.now(tz)
    
    def get_current_date(self) -> date:
        """Получить текущую дату в часовом поясе пользователя"""
        return self.get_current_datetime().date()
    
    def set_timezone(self, timezone_code: str) -> bool:
        """Установить часовой пояс пользователя"""
        if timezone_code not in AVAILABLE_TIMEZONES:
            return False
        
        self.timezone_code = timezone_code
        
        db = get_db()
        try:
            user = db.query(User).filter(User.id == self.user_id).first()
            if user:
                user.timezone_code = timezone_code
                db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при установке часового пояса: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def get_timezone_name(self) -> str:
        """Получить название часового пояса"""
        return AVAILABLE_TIMEZONES.get(self.timezone_code, "Europe/Moscow")
    
    def get_timezone_offset(self) -> str:
        """Получить смещение часового пояса относительно UTC"""
        tz = self.timezone
        now = datetime.utcnow()
        offset = tz.utcoffset(now)
        if offset is None:
            return "UTC+0"
        hours = offset.total_seconds() // 3600
        minutes = (offset.total_seconds() % 3600) // 60
        
        if hours == 0 and minutes == 0:
            return "UTC+0"
        
        sign = "+" if hours >= 0 else "-"
        hours = abs(hours)
        minutes = abs(minutes)
        
        if minutes == 0:
            return f"UTC{sign}{int(hours)}"
        else:
            return f"UTC{sign}{int(hours)}:{int(minutes):02d}"
    
    def add_food_entry(self, food_name: str, calories: float, protein: float, fat: float, carbs: float) -> Dict[str, Any]:
        """
        Добавить новую запись о еде и вернуть её
        
        Args:
            food_name: Название еды
            calories: Калории
            protein: Белки (г)
            fat: Жиры (г)
            carbs: Углеводы (г)
            
        Returns:
            Словарь с данными о созданной записи
        """
        current_time = self.get_current_datetime()
        
        db = get_db()
        try:
            # Создаем новую запись о приеме пищи
            entry = FoodEntry(
                user_id=self.user_id,
                food_name=food_name,
                calories=calories,
                protein=protein,
                fat=fat,
                carbs=carbs,
                timestamp=current_time
            )
            
            db.add(entry)
            db.commit()
            db.refresh(entry)
            
            return entry.to_dict()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении записи о еде: {e}")
            db.rollback()
            return {
                "id": 0,
                "food_name": food_name,
                "calories": calories,
                "protein": protein,
                "fat": fat,
                "carbs": carbs,
                "timestamp": current_time.isoformat()
            }
        finally:
            db.close()
    
    def set_calorie_limit(self, limit: int) -> None:
        """Установить дневной лимит калорий"""
        if limit <= 0:
            return
            
        self.calorie_limit = limit
        
        db = get_db()
        try:
            user = db.query(User).filter(User.id == self.user_id).first()
            if user:
                user.calorie_limit = limit
                db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при установке лимита калорий: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_stats_by_date(self, target_date: date) -> Dict[str, Any]:
        """Получить статистику питания за конкретную дату"""
        # Формируем диапазон времени для выбранной даты (от 00:00 до 23:59:59)
        target_start = datetime.combine(target_date, datetime.min.time())
        # Создаем осведомленную о часовом поясе дату
        tz = self.timezone
        try:
            # Пробуем сначала использовать localize метод (pytz)
            target_start = tz.localize(target_start)
        except AttributeError:
            # Если нет метода localize, используем стандартный replace (для zoneinfo)
            target_start = target_start.replace(tzinfo=tz)
        
        target_end = target_start + timedelta(days=1, seconds=-1)
        
        # Конвертируем в UTC для SQL-запроса
        target_start_utc = target_start.astimezone(pytz.UTC)
        target_end_utc = target_end.astimezone(pytz.UTC)
        
        db = get_db()
        try:
            # Получаем суммарные показатели за день
            stats = db.query(
                func.count(FoodEntry.id).label("entries"),
                func.sum(FoodEntry.calories).label("calories"),
                func.sum(FoodEntry.protein).label("protein"),
                func.sum(FoodEntry.fat).label("fat"),
                func.sum(FoodEntry.carbs).label("carbs")
            ).filter(
                FoodEntry.user_id == self.user_id,
                FoodEntry.timestamp >= target_start_utc,
                FoodEntry.timestamp <= target_end_utc
            ).first()
            
            entries = stats[0] or 0
            calories = stats[1] or 0
            protein = stats[2] or 0
            fat = stats[3] or 0
            carbs = stats[4] or 0
            
            # Вычисляем процент от дневного лимита калорий
            calorie_percentage = 0
            if self.calorie_limit and self.calorie_limit > 0:
                calorie_percentage = min(100, (calories / self.calorie_limit) * 100)
            
            return {
                "date": target_date.strftime("%d.%m.%Y"),
                "entries": entries,
                "calories": round(calories, 1),
                "protein": round(protein, 1),
                "fat": round(fat, 1),
                "carbs": round(carbs, 1),
                "calorie_limit": self.calorie_limit,
                "calorie_percentage": round(calorie_percentage, 1)
            }
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {
                "date": target_date.strftime("%d.%m.%Y"),
                "entries": 0,
                "calories": 0,
                "protein": 0,
                "fat": 0,
                "carbs": 0,
                "calorie_limit": self.calorie_limit,
                "calorie_percentage": 0
            }
        finally:
            db.close()
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Получить статистику питания за сегодня"""
        current_date = self.get_current_date()
        return self.get_stats_by_date(current_date)
    
    def get_entries_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Получить приемы пищи за конкретную дату"""
        # Формируем диапазон времени для выбранной даты (от 00:00 до 23:59:59)
        target_start = datetime.combine(target_date, datetime.min.time())
        # Создаем осведомленную о часовом поясе дату
        tz = self.timezone
        try:
            # Пробуем сначала использовать localize метод (pytz)
            target_start = tz.localize(target_start)
        except AttributeError:
            # Если нет метода localize, используем стандартный replace (для zoneinfo)
            target_start = target_start.replace(tzinfo=tz)
        
        target_end = target_start + timedelta(days=1, seconds=-1)
        
        # Конвертируем в UTC для SQL-запроса
        target_start_utc = target_start.astimezone(pytz.UTC)
        target_end_utc = target_end.astimezone(pytz.UTC)
        
        db = get_db()
        try:
            entries = db.query(FoodEntry).filter(
                FoodEntry.user_id == self.user_id,
                FoodEntry.timestamp >= target_start_utc,
                FoodEntry.timestamp <= target_end_utc
            ).order_by(FoodEntry.timestamp.desc()).all()
            
            return [entry.to_dict() for entry in entries]
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении записей о еде: {e}")
            return []
        finally:
            db.close()
    
    def get_today_entries(self) -> List[Dict[str, Any]]:
        """Получить приемы пищи за сегодня"""
        current_date = self.get_current_date()
        return self.get_entries_by_date(current_date)
    
    def delete_entry(self, entry_id: int) -> bool:
        """Удалить запись о приеме пищи по ID"""
        db = get_db()
        try:
            entry = db.query(FoodEntry).filter(
                FoodEntry.id == entry_id, 
                FoodEntry.user_id == self.user_id
            ).first()
            
            if entry:
                db.delete(entry)
                db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении записи о еде: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def delete_entry_by_index(self, index: int) -> bool:
        """Удалить запись о приеме пищи по индексу из текущих записей"""
        # Получаем записи за сегодня
        current_date = self.get_current_date()
        entries = self.get_entries_by_date(current_date)
        
        # Проверяем корректность индекса
        if index < 0 or index >= len(entries):
            return False
        
        # Получаем ID записи для удаления
        entry_id = entries[index]["id"]
        return self.delete_entry(entry_id)
    
    def get_last_week_dates(self) -> List[date]:
        """Получить список дат за последнюю неделю, включая сегодня"""
        today = self.get_current_date()
        return [today - timedelta(days=i) for i in range(7)]
    
    def generate_calorie_progress_bar(self, percentage: float, width: int = 10) -> str:
        """Создать текстовый прогресс-бар для потребления калорий"""
        filled_chars = min(int(percentage / 100 * width), width)
        empty_chars = width - filled_chars
        
        if percentage < 85:
            bar_char = "🟩"  # Зеленый для нормального употребления
        elif percentage < 100:
            bar_char = "🟨"  # Желтый для приближения к лимиту
        else:
            bar_char = "🟥"  # Красный для превышения лимита
            
        return f"{bar_char * filled_chars}{'⬜' * empty_chars} {int(percentage)}%"
    
    def generate_nutrient_progress_bar(self, value: float, target: float, nutrient_type: str, width: int = 10) -> str:
        """
        Создать текстовый прогресс-бар для потребления нутриентов (белки, жиры, углеводы)
        
        Args:
            value: Текущее количество нутриента
            target: Целевое количество нутриента
            nutrient_type: Тип нутриента ('protein', 'fat', 'carbs')
            width: Ширина прогресс-бара
            
        Returns:
            Отформатированная строка прогресс-бара с процентами
        """
        if target <= 0:
            # Если цель не установлена, используем стандартные значения
            if nutrient_type == "protein":
                target = 75  # 75г белка - стандартная рекомендация
            elif nutrient_type == "fat":
                target = 60  # 60г жиров - стандартная рекомендация
            elif nutrient_type == "carbs":
                target = 250  # 250г углеводов - стандартная рекомендация
        
        percentage = min(100, int(value / target * 100)) if target > 0 else 0
        filled_chars = min(int(percentage / 100 * width), width)
        empty_chars = width - filled_chars
        
        # Выбираем эмодзи в зависимости от типа нутриента
        if nutrient_type == "protein":
            bar_char = "🔵"  # Синий для белков
        elif nutrient_type == "fat":
            bar_char = "🟡"  # Жёлтый для жиров
        elif nutrient_type == "carbs":
            bar_char = "🟠"  # Оранжевый для углеводов
        else:
            bar_char = "⬛"  # Чёрный для неизвестного типа
            
        return f"{bar_char * filled_chars}{'⬜' * empty_chars} {int(percentage)}%"

# Кэш данных пользователей для оптимизации
db_user_data_cache: Dict[int, DBUserData] = {}

# Инициализация базы данных
init_db()

# Функция для получения данных пользователя
def get_user_data(user_id: int) -> DBUserData:
    """Получить или создать данные пользователя из базы данных"""
    # Сначала проверяем кэш, чтобы сократить количество обращений к БД
    if user_id not in db_user_data_cache:
        db_user_data_cache[user_id] = DBUserData(user_id)
    return db_user_data_cache[user_id]