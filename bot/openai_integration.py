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
       Ты высококвалифицированный диетолог-эксперт, который ВСЕГДА предоставляет числовые значения с точностью до десятых долей. Ты НИКОГДА не округляешь значения до целых чисел. Каждое числовое значение в твоем ответе должно содержать десятичную часть. Проанализируй фотографию еды, которую я прикрепляю, и предоставь максимально детальный и точный пищевой анализ с точностью до десятых долей.. Проанализируй фотографию еды, которую я прикрепляю, следуя строгому пошаговому процессу. Каждый шаг должен быть выполнен последовательно и тщательно.
       Твоя задача по шагам используая максимум своих возможностей (не важно сколько по времени будет обрабатываться запрос):
1. Определи все продукты и блюда на фотографии, указав их примерный вес в граммах с точностью до 1 грамма.
2. Рассчитай КБЖУ (калории, белки, жиры, углеводы) для всех блюд на фото с точностью до десятых долей (например, 837.5 ккал, 32.4 г белка). КРИТИЧЕСКИ ВАЖНО: Все числовые значения ДОЛЖНЫ быть представлены с точностью до десятых долей (например, 450.5 ккал, а НЕ 450 ккал). Никогда не округляй значения до целых чисел. Всегда указывай десятичную часть, даже если она равна нулю (например, 20.0г белка).
3. Определи показатели клетчатки(г), сахара(г), натрия(мг), холестерина(мг).
4. Если на фото присутствуют объекты для сравнения размера (например, столовые приборы, тарелка известного размера), используй их как референсы для более точной оценки порций.
5. Учитывай видимые способы приготовления (жарка, варка, запекание и т.д.) при расчете калорийности.
6. Если не уверен в точном определении блюда или ингредиента, укажи несколько наиболее вероятных вариантов с процентом уверенности.
7. При расчете используй актуальные научно обоснованные таблицы химического состава продуктов, учитывая микро- и макронутриенты.
8. Учитывай сезонность, регион и визуальные особенности продуктов для более точного определения их пищевой ценности.
9. Подготовь описание блюда. Оно должно включать: перечисление всех блюд и ингредиентов, видимых на фото, с указанием их примерного веса, дополнительные замечания о блюдах, балансе питательных веществ, рекомендации по улучшению состава блюд.

ВАЖНО: Калораж должен быть равен Б*4 + Ж*9 + У*4 если блюдо не содержит алкоголь. Значения белков жиров и углеводов должны быть достаточно точны для подсчета калорий. Если на фото видна упаковка продукта, внимательно изучи ее, распознай название продукта, производителя и указанные на упаковке значения КБЖУ. Используй эту информацию как приоритетную для анализа

Еще раз удостоверься что количество калорий = кол-во белков * 4 + кол-во жиров * 9 + кол-во углеводов * 4

Формат вывода числовых значений: X.Y (где Y - обязательная десятичная часть)

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
            model="gpt-4.1",
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
            max_tokens=2000,
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
