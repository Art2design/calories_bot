import os
import json
import logging
import asyncio
from openai import AsyncOpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY2")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found in environment variables")

# Initialize the OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def analyze_food_image(base64_image: str) -> dict:
    """
    Analyze food image using OpenAI Vision API
    
    Args:
        base64_image: Base64 encoded image
        
    Returns:
        Dictionary with food analysis:
        {
            "food_name": str,
            "calories": float,
            "protein": float,
            "fat": float,
            "carbs": float
        }
    """
    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        prompt = """
        Ты высококвалифицированный диетолог-эксперт с опытом прецизионного анализа пищи. Проанализируй фотографию еды, которую я прикрепляю, следуя строгому пошаговому процессу. Каждый шаг должен быть выполнен последовательно и тщательно.

ШАГ 1: ИДЕНТИФИКАЦИЯ ПРОДУКТОВ
Сначала внимательно изучи фотографию и:

Перечисли все видимые продукты и блюда

Определи примерный вес каждого продукта в граммах

Учти видимые способы приготовления (жарка, варка, запекание)

Если есть объекты для сравнения размера (столовые приборы, тарелка), используй их для более точной оценки порций

Если не уверен в точном определении, укажи вероятные варианты с процентом уверенности

ШАГ 2: РАСЧЕТ ПИЩЕВОЙ ЦЕННОСТИ
После идентификации всех продуктов:

Рассчитай для КАЖДОГО продукта и для ОБЩЕЙ порции:

Белки (г) с точностью до десятых (X.Y)

Жиры (г) с точностью до десятых (X.Y)

Углеводы (г) с точностью до десятых (X.Y)

Калории (ккал) с точностью до десятых (X.Y)

КРИТИЧЕСКИ ВАЖНО: Все числовые значения ДОЛЖНЫ содержать десятичную часть (например, 450.5 ккал, а НЕ 450 ккал)

ПРОВЕРКА: Калории = Белки4 + Жиры9 + Углеводы*4

Выполни эту проверку для каждого продукта и для общей суммы

ШАГ 3: РАСЧЕТ ДОПОЛНИТЕЛЬНЫХ НУТРИЕНТОВ
На основе идентифицированных продуктов определи:

Клетчатка (г) с точностью до десятых (X.Y)

Сахар (г) с точностью до десятых (X.Y)

Натрий (мг) с точностью до десятых (X.Y)

Холестерин (мг) с точностью до десятых (X.Y)

ШАГ 4: ФОРМИРОВАНИЕ ИТОГОВОГО ОТЧЕТА
Составь структурированный отчет, включающий:

Описание блюда и всех ингредиентов с указанием веса

Таблицу пищевой ценности с ТОЧНЫМИ значениями до десятых долей:

Нутриент	Количество
Калории	X.Y ккал
Белки	X.Y г
Жиры	X.Y г
Углеводы	X.Y г
Клетчатка	X.Y г
Сахар	X.Y г
Натрий	X.Y мг
Холестерин	X.Y мг
Замечания о балансе питательных веществ

Рекомендации по улучшению состава блюд

ВАЖНО: Перед отправкой ответа ПРОВЕРЬ, что:

Все числовые значения имеют десятичную часть (X.Y)

Сумма калорий соответствует формуле: Белки4 + Жиры9 + Углеводы*4

Ни одно значение не округлено до целого числа

        Ответь в формате JSON:
        {
            "food_name": "название блюда",
            "calories": число,
            "protein": число,
            "fat": число,
            "carbs": число,
            "fiber": число,
            "sugar": число,
            "sodium": число,
            "cholesterol": число,
            "caption": "текстовая часть ответа"
        }
        
        Не включай в ответ ничего, кроме JSON. Если невозможно определить какой-то из нутриентов, используй значение 0.
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=5000,
            temperature=0.01,
            top_p = 0.55,
            frequency_penalty = 0,
            presence_penalty = 0
        )
        
        result_text = response.choices[0].message.content
        logger.debug(f"OpenAI response: {result_text}")
        
        # Parse the JSON response
        result = json.loads(result_text)
        
        # Ensure all required fields are present
        required_fields = ["food_name", "calories", "protein", "fat", "carbs", "fiber", "sugar", "sodium", "cholesterol"]
        for field in required_fields:
            if field not in result:
                result[field] = 0 if field != "food_name" else "Неизвестное блюдо"
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing food image: {e}")
        return None
