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
    "EET": "Europe/Kyiv",         # Восточноевропейское время UTC+2
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
    "KYIV": "Europe/Kyiv",        # Киев UTC+2
}

class DBUserData:
    """Класс для работы с данными пользователя в базе данных"""

    def __init__(self, user_id: int):
        """Инициализация данных пользователя, загрузка из базы или создание новой записи"""
        self.user_id = user_id
        self.calorie_limit = None
        self.protein_limit = None
        self.fat_limit = None
        self.carbs_limit = None
        self.fiber_limit = None
        self.user_weight = None
        self.body_fat_percentage = None
        self.timezone_code = "МСК"
        self.load_from_db()

    def load_from_db(self):
        """Загрузить данные пользователя из базы"""
        db = get_db()
        try:
            user = db.query(User).filter(User.id == self.user_id).first()
            if user:
                self.calorie_limit = user.calorie_limit
                self.protein_limit = user.protein_limit
                self.fat_limit = user.fat_limit
                self.carbs_limit = user.carbs_limit
                self.fiber_limit = user.fiber_limit
                self.user_weight = user.user_weight
                self.body_fat_percentage = user.body_fat_percentage
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
        # Проверяем, есть ли код в словаре или используем Москву по умолчанию
        try:
            tz_name = AVAILABLE_TIMEZONES.get(self.timezone_code)
            if not tz_name:
                tz_name = "Europe/Moscow"
                logger.warning(f"Неизвестный код часового пояса: {self.timezone_code}, используем Europe/Moscow")
                # Исправляем код часового пояса на правильный
                self.timezone_code = "МСК"
                # Сохраняем исправленный код в базу
                self.set_timezone("МСК")

            # Возвращаем объект часового пояса
            return pytz.timezone(tz_name)
        except Exception as e:
            logger.error(f"Ошибка при получении часового пояса: {e}")
            # Если произошла ошибка, возвращаем часовой пояс Москвы
            return pytz.timezone("Europe/Moscow")

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
        # Проверяем, есть ли код в словаре или используем Москву по умолчанию
        try:
            tz_name = AVAILABLE_TIMEZONES.get(self.timezone_code)
            if not tz_name:
                tz_name = "Europe/Moscow"
                logger.warning(f"Неизвестный код часового пояса при получении имени: {self.timezone_code}, используем Europe/Moscow")
                # Исправляем код часового пояса на правильный
                self.timezone_code = "МСК"
                # Сохраняем исправленный код в базу
                self.set_timezone("МСК")
            return tz_name
        except Exception as e:
            logger.error(f"Ошибка при получении названия часового пояса: {e}")
            return "Europe/Moscow"

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

    def add_food_entry(self, food_name: str, calories: float, protein: float, fat: float, carbs: float, 
                      fiber: float = 0, sugar: float = 0, sodium: float = 0, cholesterol: float = 0) -> Dict[str, Any]:
        """
        Добавить новую запись о еде и вернуть её

        Args:
            food_name: Название еды
            calories: Калории
            protein: Белки (г)
            fat: Жиры (г)
            carbs: Углеводы (г)
            fiber: Клетчатка (г)
            sugar: Сахар (г)
            sodium: Натрий (мг)
            cholesterol: Холестерин (мг)

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
                fiber=fiber,
                sugar=sugar,
                sodium=sodium,
                cholesterol=cholesterol,
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
                "fiber": fiber,
                "sugar": sugar,
                "sodium": sodium,
                "cholesterol": cholesterol,
                "timestamp": current_time.isoformat()
            }
        finally:
            db.close()

    def update_food_entry(self, entry_id: int, fiber: float = None, sugar: float = None, 
                          sodium: float = None, cholesterol: float = None) -> bool:
        """
        Обновить существующую запись о еде дополнительными нутриентами

        Args:
            entry_id: ID записи
            fiber: Клетчатка (г)
            sugar: Сахар (г)
            sodium: Натрий (мг)
            cholesterol: Холестерин (мг)

        Returns:
            bool: Успешно ли обновлена запись
        """
        db = get_db()
        try:
            # Находим запись
            entry = db.query(FoodEntry).filter(
                FoodEntry.id == entry_id,
                FoodEntry.user_id == self.user_id
            ).first()

            if not entry:
                return False

            # Обновляем только переданные параметры
            if fiber is not None:
                entry.fiber = fiber
            if sugar is not None:
                entry.sugar = sugar
            if sodium is not None:
                entry.sodium = sodium
            if cholesterol is not None:
                entry.cholesterol = cholesterol

            db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении записи о еде: {e}")
            db.rollback()
            return False
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

    def set_macros_limits(self, protein: float, fat: float, carbs: float, fiber: Optional[float] = None, 
                       sugar: Optional[float] = None, sodium: Optional[float] = None, 
                       cholesterol: Optional[float] = None) -> bool:
        """
        Установить дневные лимиты макронутриентов

        Args:
            protein: Лимит белков (г)
            fat: Лимит жиров (г)
            carbs: Лимит углеводов (г)
            fiber: Лимит клетчатки (г)
            sugar: Лимит сахара (г)
            sodium: Лимит натрия (мг)
            cholesterol: Лимит холестерина (мг)

        Returns:
            bool: Успешно ли установлены лимиты
        """
        if protein <= 0 or fat <= 0 or carbs <= 0:
            return False

        self.protein_limit = protein
        self.fat_limit = fat
        self.carbs_limit = carbs

        # Устанавливаем дополнительные лимиты, если они заданы
        # Не используем проверку > 0, т.к. это приводит к ошибке, если fiber is None
        if fiber is not None:
            self.fiber_limit = fiber
        if sugar is not None:
            self.sugar_limit = sugar
        if sodium is not None:
            self.sodium_limit = sodium
        if cholesterol is not None:
            self.cholesterol_limit = cholesterol

        # Рассчитываем калории на основе КБЖУ
        calories = protein * 4 + fat * 9 + carbs * 4
        self.calorie_limit = int(calories)

        db = get_db()
        try:
            user = db.query(User).filter(User.id == self.user_id).first()
            if user:
                user.protein_limit = protein
                user.fat_limit = fat
                user.carbs_limit = carbs
                user.calorie_limit = int(calories)

                # Обновляем дополнительные лимиты в базе данных
                if fiber is not None and fiber > 0:
                    user.fiber_limit = fiber
                if sugar is not None and sugar > 0:
                    user.sugar_limit = sugar
                if sodium is not None and sodium > 0:
                    user.sodium_limit = sodium
                if cholesterol is not None and cholesterol > 0:
                    user.cholesterol_limit = cholesterol

                db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при установке лимита макронутриентов: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def set_user_body_metrics(self, weight: float, body_fat: float) -> bool:
        """
        Установить метрики тела пользователя и рассчитать рекомендуемые значения КБЖУ

        Args:
            weight: Вес в кг
            body_fat: Процент жира в теле (0-100)

        Returns:
            bool: Успешно ли установлены метрики
        """
        if weight <= 0 or body_fat < 0 or body_fat > 100:
            return False

        self.user_weight = weight
        self.body_fat_percentage = body_fat

        # Рассчитываем лимиты макронутриентов на основе веса и % жира
        # Простой алгоритм:
        # Расчет безжировой массы тела (LBM)
        lean_body_mass = weight * (1 - body_fat / 100)

        # Расчет целевых значений
        protein = round(lean_body_mass * 2, 1)  # 2г белка на кг LBM
        fat = round(weight * 1, 1)  # 1г жира на кг веса
        carbs = round(weight * 3, 1)  # 3г углеводов на кг веса
        fiber = round(weight * 0.3, 1)  # 0.3г клетчатки на кг веса
        sugar = round(weight * 0.5, 1)  # 0.5г сахара на кг веса (лимит)
        sodium = round(weight * 20, 1)  # 20мг натрия на кг веса
        cholesterol = round(weight * 3, 1)  # 3мг холестерина на кг веса

        # Устанавливаем рассчитанные лимиты
        self.set_macros_limits(
            protein=protein, 
            fat=fat, 
            carbs=carbs, 
            fiber=fiber,
            sugar=sugar,
            sodium=sodium,
            cholesterol=cholesterol
        )

        db = get_db()
        try:
            user = db.query(User).filter(User.id == self.user_id).first()
            if user:
                user.user_weight = weight
                user.body_fat_percentage = body_fat
                db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при установке метрик тела: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def get_stats_by_date(self, target_date: date) -> Dict[str, Any]:
        """Получить статистику питания за конкретную дату"""
        try:
            # Более безопасный метод создания даты с часовым поясом
            tz = self.timezone
            # Создаем осведомленный о часовом поясе datetime в полночь целевой даты
            target_start = datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=0, minute=0, second=0, microsecond=0,
                tzinfo=pytz.UTC
            ).astimezone(tz)
        except Exception as e:
            logger.error(f"Ошибка при создании даты с часовым поясом: {e}")
            # Создаем дату в UTC если произошла ошибка
            target_start = datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=0, minute=0, second=0, microsecond=0,
                tzinfo=pytz.UTC
            )

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
                func.sum(FoodEntry.carbs).label("carbs"),
                func.sum(FoodEntry.fiber).label("fiber"),
                func.sum(FoodEntry.sugar).label("sugar"),
                func.sum(FoodEntry.sodium).label("sodium"),
                func.sum(FoodEntry.cholesterol).label("cholesterol")
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
            fiber = stats[5] or 0
            sugar = stats[6] or 0
            sodium = stats[7] or 0
            cholesterol = stats[8] or 0

            # Вычисляем проценты от лимитов
            calorie_percentage = 0
            if self.calorie_limit and self.calorie_limit > 0:
                calorie_percentage = min(100, (calories / self.calorie_limit) * 100)

            protein_percentage = 0
            if self.protein_limit and self.protein_limit > 0:
                protein_percentage = min(100, (protein / self.protein_limit) * 100)

            fat_percentage = 0
            if self.fat_limit and self.fat_limit > 0:
                fat_percentage = min(100, (fat / self.fat_limit) * 100)

            carbs_percentage = 0
            if self.carbs_limit and self.carbs_limit > 0:
                carbs_percentage = min(100, (carbs / self.carbs_limit) * 100)

            fiber_percentage = 0
            if self.fiber_limit and self.fiber_limit > 0:
                fiber_percentage = min(100, (fiber / self.fiber_limit) * 100)
                
            # Рассчитываем проценты для дополнительных нутриентов
            sugar_percentage = 0
            if hasattr(self, 'sugar_limit') and self.sugar_limit and self.sugar_limit > 0:
                sugar_percentage = min(100, (sugar / self.sugar_limit) * 100)
                
            sodium_percentage = 0
            if hasattr(self, 'sodium_limit') and self.sodium_limit and self.sodium_limit > 0:
                sodium_percentage = min(100, (sodium / self.sodium_limit) * 100)
                
            cholesterol_percentage = 0
            if hasattr(self, 'cholesterol_limit') and self.cholesterol_limit and self.cholesterol_limit > 0:
                cholesterol_percentage = min(100, (cholesterol / self.cholesterol_limit) * 100)

            return {
                "date": target_date.strftime("%d.%m.%Y"),
                "entries": entries,
                "calories": round(calories, 1),
                "protein": round(protein, 1),
                "fat": round(fat, 1),
                "carbs": round(carbs, 1),
                "fiber": round(fiber, 1),
                "sugar": round(sugar, 1),
                "sodium": round(sodium, 1),
                "cholesterol": round(cholesterol, 1),

                # Лимиты
                "calorie_limit": self.calorie_limit,
                "protein_limit": self.protein_limit,
                "fat_limit": self.fat_limit,
                "carbs_limit": self.carbs_limit,
                "fiber_limit": self.fiber_limit,
                "sugar_limit": getattr(self, 'sugar_limit', None),
                "sodium_limit": getattr(self, 'sodium_limit', None),
                "cholesterol_limit": getattr(self, 'cholesterol_limit', None),

                # Проценты выполнения
                "calorie_percentage": round(calorie_percentage, 1),
                "protein_percentage": round(protein_percentage, 1),
                "fat_percentage": round(fat_percentage, 1),
                "carbs_percentage": round(carbs_percentage, 1),
                "fiber_percentage": round(fiber_percentage, 1),
                "sugar_percentage": round(sugar_percentage, 1),
                "sodium_percentage": round(sodium_percentage, 1),
                "cholesterol_percentage": round(cholesterol_percentage, 1)
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
                "fiber": 0,
                "sugar": 0,
                "sodium": 0,
                "cholesterol": 0,

                # Лимиты
                "calorie_limit": self.calorie_limit,
                "protein_limit": self.protein_limit,
                "fat_limit": self.fat_limit,
                "carbs_limit": self.carbs_limit,
                "fiber_limit": self.fiber_limit,
                "sugar_limit": getattr(self, 'sugar_limit', None),
                "sodium_limit": getattr(self, 'sodium_limit', None),
                "cholesterol_limit": getattr(self, 'cholesterol_limit', None),

                # Проценты выполнения
                "calorie_percentage": 0,
                "protein_percentage": 0,
                "fat_percentage": 0,
                "carbs_percentage": 0,
                "fiber_percentage": 0,
                "sugar_percentage": 0,
                "sodium_percentage": 0,
                "cholesterol_percentage": 0
            }
        finally:
            db.close()

    def get_today_stats(self) -> Dict[str, Any]:
        """Получить статистику питания за сегодня"""
        current_date = self.get_current_date()
        return self.get_stats_by_date(current_date)

    def get_entries_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Получить приемы пищи за конкретную дату"""
        try:
            # Более безопасный метод создания даты с часовым поясом
            tz = self.timezone
            # Создаем осведомленный о часовом поясе datetime в полночь целевой даты
            target_start = datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=0, minute=0, second=0, microsecond=0,
                tzinfo=pytz.UTC
            ).astimezone(tz)
        except Exception as e:
            logger.error(f"Ошибка при создании даты с часовым поясом: {e}")
            # Создаем дату в UTC если произошла ошибка
            target_start = datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=0, minute=0, second=0, microsecond=0,
                tzinfo=pytz.UTC
            )

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

    def generate_nutrient_progress_bar(self, value: float, target: Optional[float], nutrient_type: str, width: int = 10) -> str:
        """
        Generate a text progress bar for nutrient consumption

        Args:
            value: Current amount of nutrient consumed
            target: Target amount of nutrient
            nutrient_type: Type of nutrient ('protein', 'fat', 'carbs', 'fiber', 'sugar', 'sodium', 'cholesterol')
            width: Width of the progress bar

        Returns:
            Formatted progress bar string with percentage
        """
        if target is None or target <= 0:
            # Если цель не установлена, используем стандартные значения в зависимости от типа нутриента
            if nutrient_type == "protein":
                target = 75  # 75г белка - стандартная рекомендация
            elif nutrient_type == "fat":
                target = 60  # 60г жиров - стандартная рекомендация
            elif nutrient_type == "carbs":
                target = 250  # 250г углеводов - стандартная рекомендация
            elif nutrient_type == "fiber":
                target = 25  # 25г клетчатки - стандартная рекомендация
            elif nutrient_type == "sugar":
                target = 50  # 50г сахара - верхний предел по рекомендациям ВОЗ
            elif nutrient_type == "sodium":
                target = 2300  # 2300мг натрия - рекомендация ВОЗ
            elif nutrient_type == "cholesterol":
                target = 300  # 300мг холестерина - стандартная рекомендация

        # Рассчитываем процент выполнения
        target_value = float(target) if target else 0
        percentage = min(100, int(value / target_value * 100)) if target_value > 0 else 0
        filled_chars = min(int(percentage / 100 * width), width)
        empty_chars = width - filled_chars

        # Выбираем эмодзи в зависимости от типа нутриента
        if nutrient_type == "protein":
            bar_char = "🔵"  # Синий для белков
        elif nutrient_type == "fat":
            bar_char = "🟡"  # Жёлтый для жиров
        elif nutrient_type == "carbs":
            bar_char = "🟠"  # Оранжевый для углеводов
        elif nutrient_type == "fiber":
            bar_char = "🟢"  # Зелёный для клетчатки
        elif nutrient_type == "sugar":
            bar_char = "🟣"  # Фиолетовый для сахара
        elif nutrient_type == "sodium":
            bar_char = "⚪"  # Белый для натрия
        elif nutrient_type == "cholesterol":
            bar_char = "🔴"  # Красный для холестерина
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