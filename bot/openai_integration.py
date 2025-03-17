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
        Ты опытный диетолог-эксперт по анализу пищи. Проанализируй фотографию еды, которую я прикрепляю, и предоставь детальный пищевой анализ.

        Твоя задача:
        1. Определи все продукты и блюда на фотографии, указав их примерный вес в граммах.
        2. Рассчитай точные показатели КБЖУ (калории, белки, жиры, углеводы) для всех блюд на фото.
        3. Определи примерные показатели клетчатки(г), сахара(г), натрия(мг), холестерина(мг).
        4. Если на фото присутствуют объекты для сравнения размера (например, столовые приборы, тарелка известного размера), используй их как референсы для более точной оценки порций.
        5. Учитывай видимые способы приготовления (жарка, варка, запекание и т.д.) при расчете калорийности.
        6. Если не уверен в точном определении блюда или ингредиента, укажи несколько наиболее вероятных вариантов с процентом уверенности.
        7. Подготовь описание блюда. Оно должно включать: перечисление всех блюд и ингредиентов, видимых на фото, с указанием их примерного веса, дополнительные замечания о блюдах, балансе питательных веществ, рекомендации по улучшению состава блюд.

        ВАЖНО: Значения белков жиров и углеводов должны быть достаточно точны для подсчета калорий. Калораж должен быть равен Б*4 + Ж*9 + У*4 если блюдо не содержит алкоголь.
        
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
            max_tokens=500,
            temperature=0.2,
            top_p=0.1          
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
