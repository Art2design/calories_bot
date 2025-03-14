from datetime import datetime, date, timedelta, tzinfo
from typing import Dict, List, Optional, Any, Tuple
import pytz

# Список часовых поясов России и популярных стран
AVAILABLE_TIMEZONES = {
    "МСК": "Europe/Moscow",  # Москва (UTC+3)
    "КЛД": "Europe/Kaliningrad",  # Калининград (UTC+2)
    "СПБ": "Europe/Moscow",  # Санкт-Петербург (UTC+3)
    "ЕКБ": "Asia/Yekaterinburg",  # Екатеринбург (UTC+5)
    "НСК": "Asia/Novosibirsk",  # Новосибирск (UTC+7)
    "ИРК": "Asia/Irkutsk",  # Иркутск (UTC+8)
    "ВЛД": "Asia/Vladivostok",  # Владивосток (UTC+10)
    "КМЧ": "Asia/Kamchatka",  # Камчатка (UTC+12)
    "КИВ": "Europe/Kiev",  # Киев (UTC+2)
    "МНК": "Asia/Minsk",  # Минск (UTC+3)
    "АСТ": "Asia/Almaty",  # Алматы (UTC+6)
    "ТШК": "Asia/Tashkent",  # Ташкент (UTC+5)
    "БКУ": "Asia/Baku",  # Баку (UTC+4)
    "УТС": "UTC",  # Всемирное координированное время (UTC)
}

# Часовой пояс по умолчанию - Москва
DEFAULT_TIMEZONE = "МСК"  # Europe/Moscow

class FoodEntry:
    """Food entry class for storing individual food items"""
    def __init__(self, food_name: str, calories: float, protein: float, fat: float, carbs: float, tz: Optional[tzinfo] = None):
        self.food_name = food_name
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        
        # Используем указанный часовой пояс или UTC
        if tz:
            self.timestamp = datetime.now(tz)
        else:
            self.timestamp = datetime.now(pytz.UTC)
            
        self.id = int(self.timestamp.timestamp())  # Уникальный ID на основе времени
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert food entry to dictionary"""
        return {
            "id": self.id,
            "food_name": self.food_name,
            "calories": self.calories,
            "protein": self.protein,
            "fat": self.fat,
            "carbs": self.carbs,
            "timestamp": self.timestamp.isoformat()
        }

class UserData:
    """User data class for storing user information and food entries"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.calorie_limit: Optional[int] = None
        self.food_entries: List[FoodEntry] = []
        self.timezone_code: str = DEFAULT_TIMEZONE  # Код часового пояса (например, "МСК")
        
    @property
    def timezone(self) -> tzinfo:
        """Получить объект часового пояса пользователя"""
        tz_name = AVAILABLE_TIMEZONES.get(self.timezone_code, "Europe/Moscow")
        return pytz.timezone(tz_name)
    
    def get_current_datetime(self) -> datetime:
        """Получить текущее время в часовом поясе пользователя"""
        return datetime.now(self.timezone)
    
    def get_current_date(self) -> date:
        """Получить текущую дату в часовом поясе пользователя"""
        return self.get_current_datetime().date()
    
    def set_timezone(self, timezone_code: str) -> bool:
        """Установить часовой пояс пользователя"""
        if timezone_code in AVAILABLE_TIMEZONES:
            self.timezone_code = timezone_code
            return True
        return False
    
    def get_timezone_name(self) -> str:
        """Получить название часового пояса"""
        tz_name = AVAILABLE_TIMEZONES.get(self.timezone_code, "Europe/Moscow")
        return tz_name
    
    def get_timezone_offset(self) -> str:
        """Получить смещение часового пояса относительно UTC"""
        now = datetime.now(self.timezone)
        utc_offset = now.strftime("%z")
        hours = int(utc_offset[:-2])
        return f"UTC{'+' if hours >= 0 else ''}{hours}"
        
    def add_food_entry(self, food_name: str, calories: float, protein: float, fat: float, carbs: float) -> FoodEntry:
        """Add a new food entry and return it"""
        entry = FoodEntry(food_name, calories, protein, fat, carbs, tz=self.timezone)
        self.food_entries.append(entry)
        return entry
    
    def set_calorie_limit(self, limit: int) -> None:
        """Set daily calorie limit"""
        self.calorie_limit = limit
    
    def get_stats_by_date(self, target_date: date) -> Dict[str, Any]:
        """Get nutrition stats for a specific date"""
        # Получаем записи за указанную дату по часовому поясу пользователя
        date_entries = [
            entry for entry in self.food_entries
            if entry.timestamp.astimezone(self.timezone).date() == target_date
        ]
        
        # Вычисляем общие значения
        total_calories = sum(entry.calories for entry in date_entries)
        total_protein = sum(entry.protein for entry in date_entries)
        total_fat = sum(entry.fat for entry in date_entries)
        total_carbs = sum(entry.carbs for entry in date_entries)
        
        # Вычисляем процент от дневного лимита
        calorie_percentage = 0
        if self.calorie_limit and self.calorie_limit > 0:
            calorie_percentage = (total_calories / self.calorie_limit) * 100
        
        return {
            "date": target_date.strftime("%d.%m.%Y"),
            "entries": len(date_entries),
            "calories": round(total_calories, 1),
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1),
            "calorie_limit": self.calorie_limit,
            "calorie_percentage": round(calorie_percentage, 1)
        }
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Get nutrition stats for today"""
        return self.get_stats_by_date(self.get_current_date())
    
    def get_entries_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get food entries for a specific date"""
        # Фильтруем записи по дате с учетом часового пояса
        date_entries = [
            entry for entry in self.food_entries
            if entry.timestamp.astimezone(self.timezone).date() == target_date
        ]
        
        # Сортируем по времени (новые сверху)
        sorted_entries = sorted(
            date_entries,
            key=lambda entry: entry.timestamp,
            reverse=True
        )
        
        return [entry.to_dict() for entry in sorted_entries]
    
    def get_today_entries(self) -> List[Dict[str, Any]]:
        """Get food entries for today"""
        return self.get_entries_by_date(self.get_current_date())
    
    def delete_entry(self, entry_id: int) -> bool:
        """Delete a food entry by ID"""
        for i, entry in enumerate(self.food_entries):
            if entry.id == entry_id:
                del self.food_entries[i]
                return True
        return False
    
    def delete_entry_by_index(self, index: int) -> bool:
        """Delete a food entry by index"""
        # Получаем сегодняшние записи
        today_entries = [
            entry for entry in self.food_entries
            if entry.timestamp.astimezone(self.timezone).date() == self.get_current_date()
        ]
        
        # Сортируем по времени (новые сверху)
        sorted_entries = sorted(
            today_entries,
            key=lambda entry: entry.timestamp,
            reverse=True
        )
        
        if 0 <= index < len(sorted_entries):
            entry_to_delete = sorted_entries[index]
            for i, entry in enumerate(self.food_entries):
                if entry.id == entry_to_delete.id:
                    del self.food_entries[i]
                    return True
        return False
    
    def get_last_week_dates(self) -> List[date]:
        """Get list of dates for the last week including today"""
        today = self.get_current_date()
        return [today - timedelta(days=i) for i in range(7)]
    
    def generate_calorie_progress_bar(self, percentage: float, width: int = 10) -> str:
        """Generate a text progress bar for calorie consumption"""
        filled_chars = min(int(percentage / 100 * width), width)
        empty_chars = width - filled_chars
        
        if percentage < 85:
            bar_char = "🟩"  # Зеленый для нормального употребления
        elif percentage < 100:
            bar_char = "🟨"  # Желтый для приближения к лимиту
        else:
            bar_char = "🟥"  # Красный для превышения лимита
            
        return f"{bar_char * filled_chars}{'⬜' * empty_chars} {percentage}%"

# In-memory storage for user data
user_data_storage: Dict[int, UserData] = {}
