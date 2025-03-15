import os
import json
import logging
import asyncio
from openai import AsyncOpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
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
        Проанализируй это изображение еды и определи:
        1. Название блюда
        2. Приблизительное количество калорий (ккал)
        3. Примерное содержание белков (г)
        4. Примерное содержание жиров (г)
        5. Примерное содержание углеводов (г)
        6. Примерное содержание клетчатки (г)
        7. Примерное содержание сахара (г)
        8. Примерное содержание натрия (мг)
        9. Примерное содержание холестерина (мг)
        
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
            "cholesterol": число
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
            max_tokens=800
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
