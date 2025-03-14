from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple

class FoodEntry:
    """Food entry class for storing individual food items"""
    def __init__(self, food_name: str, calories: float, protein: float, fat: float, carbs: float):
        self.food_name = food_name
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        self.timestamp = datetime.now()
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
    
    def add_food_entry(self, food_name: str, calories: float, protein: float, fat: float, carbs: float) -> FoodEntry:
        """Add a new food entry and return it"""
        entry = FoodEntry(food_name, calories, protein, fat, carbs)
        self.food_entries.append(entry)
        return entry
    
    def set_calorie_limit(self, limit: int) -> None:
        """Set daily calorie limit"""
        self.calorie_limit = limit
    
    def get_stats_by_date(self, target_date: date) -> Dict[str, Any]:
        """Get nutrition stats for a specific date"""
        # Получаем записи за указанную дату
        date_entries = [
            entry for entry in self.food_entries
            if entry.timestamp.date() == target_date
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
        return self.get_stats_by_date(date.today())
    
    def get_entries_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get food entries for a specific date"""
        # Фильтруем записи по дате
        date_entries = [
            entry for entry in self.food_entries
            if entry.timestamp.date() == target_date
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
        return self.get_entries_by_date(date.today())
    
    def delete_entry(self, entry_id: int) -> bool:
        """Delete a food entry by ID"""
        for i, entry in enumerate(self.food_entries):
            if entry.id == entry_id:
                del self.food_entries[i]
                return True
        return False
    
    def delete_entry_by_index(self, index: int) -> bool:
        """Delete a food entry by index"""
        if 0 <= index < len(self.food_entries):
            del self.food_entries[index]
            return True
        return False
    
    def get_last_week_dates(self) -> List[date]:
        """Get list of dates for the last week including today"""
        today = date.today()
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
