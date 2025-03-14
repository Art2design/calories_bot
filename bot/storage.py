from datetime import datetime, date
from typing import Dict, List, Optional, Any

class FoodEntry:
    """Food entry class for storing individual food items"""
    def __init__(self, food_name: str, calories: float, protein: float, fat: float, carbs: float):
        self.food_name = food_name
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        self.timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert food entry to dictionary"""
        return {
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
    
    def add_food_entry(self, food_name: str, calories: float, protein: float, fat: float, carbs: float) -> None:
        """Add a new food entry"""
        entry = FoodEntry(food_name, calories, protein, fat, carbs)
        self.food_entries.append(entry)
    
    def set_calorie_limit(self, limit: int) -> None:
        """Set daily calorie limit"""
        self.calorie_limit = limit
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Get nutrition stats for today"""
        today = date.today()
        today_entries = [
            entry for entry in self.food_entries
            if entry.timestamp.date() == today
        ]
        
        total_calories = sum(entry.calories for entry in today_entries)
        total_protein = sum(entry.protein for entry in today_entries)
        total_fat = sum(entry.fat for entry in today_entries)
        total_carbs = sum(entry.carbs for entry in today_entries)
        
        return {
            "entries": len(today_entries),
            "calories": round(total_calories, 1),
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1)
        }
    
    def get_recent_entries(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get most recent food entries"""
        sorted_entries = sorted(
            self.food_entries, 
            key=lambda entry: entry.timestamp,
            reverse=True
        )
        return [entry.to_dict() for entry in sorted_entries[:count]]

# In-memory storage for user data
user_data_storage: Dict[int, UserData] = {}
