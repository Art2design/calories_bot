import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Получаем строку подключения к базе данных из переменной окружения
DATABASE_URL = os.environ.get("DATABASE_URL")

# Создаем базовый класс моделей
Base = declarative_base()

# Модель для пользователя
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)  # Telegram ID пользователя
    timezone_code = Column(String, default="МСК")  # Часовой пояс пользователя
    calorie_limit = Column(Integer, nullable=True)  # Дневной лимит калорий
    protein_limit = Column(Float, nullable=True)  # Дневной лимит белков
    fat_limit = Column(Float, nullable=True)  # Дневной лимит жиров
    carbs_limit = Column(Float, nullable=True)  # Дневной лимит углеводов
    fiber_limit = Column(Float, nullable=True)  # Дневной лимит клетчатки
    user_weight = Column(Float, nullable=True)  # Вес пользователя в кг
    body_fat_percentage = Column(Float, nullable=True)  # Процент жира в теле
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношение "один-ко-многим" с приемами пищи
    food_entries = relationship("FoodEntry", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, timezone_code={self.timezone_code}, calorie_limit={self.calorie_limit})>"

# Модель для приема пищи
class FoodEntry(Base):
    __tablename__ = "food_entries"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    food_name = Column(String, nullable=False)
    calories = Column(Float, default=0)
    protein = Column(Float, default=0)
    fat = Column(Float, default=0)
    carbs = Column(Float, default=0)
    fiber = Column(Float, default=0)  # Клетчатка
    sugar = Column(Float, default=0)  # Сахар
    sodium = Column(Float, default=0)  # Натрий (в мг)
    cholesterol = Column(Float, default=0)  # Холестерин (в мг)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Отношение "многие-к-одному" с пользователем
    user = relationship("User", back_populates="food_entries")
    
    def __repr__(self):
        return f"<FoodEntry(id={self.id}, user_id={self.user_id}, food_name={self.food_name}, calories={self.calories})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать запись еды в словарь"""
        return {
            "id": self.id,
            "food_name": self.food_name,
            "calories": self.calories,
            "protein": self.protein,
            "fat": self.fat,
            "carbs": self.carbs,
            "fiber": self.fiber,
            "sugar": self.sugar,
            "sodium": self.sodium,
            "cholesterol": self.cholesterol,
            "timestamp": self.timestamp.isoformat()
        }

# Создаем подключение к базе данных
engine = create_engine(DATABASE_URL, echo=False)

# Создаем все таблицы в базе данных
def init_db():
    Base.metadata.create_all(engine)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для получения сессии
def get_db() -> Session:
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()