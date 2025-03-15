import os
import logging
from sqlalchemy import create_engine, Column, Float, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к базе данных
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    exit(1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

def run_migrations():
    logger.info("Starting database migrations")
    
    try:
        # Проверяем, есть ли колонки в таблице users
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [column['name'] for column in inspector.get_columns('users')]
        
        # Список новых колонок и их типов данных
        new_columns = {
            'protein_limit': Float,
            'fat_limit': Float,
            'carbs_limit': Float,
            'fiber_limit': Float,
            'sugar_limit': Float,
            'sodium_limit': Float,
            'cholesterol_limit': Float,
            'user_weight': Float,
            'body_fat_percentage': Float
        }
        
        # Добавляем только те колонки, которых еще нет
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                logger.info(f"Adding column {column_name} to users table")
                # Используем text() для SQL-выражений
                sql_type = get_sql_type(column_type)
                alter_stmt = text(f"ALTER TABLE users ADD COLUMN {column_name} {sql_type}")
                session.execute(alter_stmt)
                logger.info(f"Column {column_name} added successfully")
            else:
                logger.info(f"Column {column_name} already exists, skipping")
        
        # Применяем изменения
        session.commit()
        logger.info("Migrations completed successfully")
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error during migration: {e}")
        raise
    finally:
        session.close()

def get_sql_type(sa_type):
    """Преобразование типа SQLAlchemy в тип SQL"""
    if sa_type == Float:
        return "FLOAT"
    return "VARCHAR"

if __name__ == "__main__":
    run_migrations()
    logger.info("Migration script completed")