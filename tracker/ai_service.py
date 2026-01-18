"""
AI Service for food logging using OpenAI GPT-4o.
Handles both text descriptions and food photo analysis.
"""
import os
import json
import base64
from datetime import date
from openai import OpenAI


FOOD_LOG_SYSTEM_PROMPT = """You are a nutrition tracking assistant. When given a description of food eaten or an image of food, extract the following information and return it as valid JSON.

Output format:
{{
  "date": "{today}",
  "dietary": [
    {{"item": "food name", "calories": estimated_calories, "notes": "optional portion/preparation notes"}}
  ],
  "remarks": "optional meal context (breakfast, lunch, dinner, snack)"
}}

Rules:
1. Always use the date: {today}
2. Estimate calories using standard USDA nutritional data
3. For images, identify all visible food items and estimate portion sizes
4. Be conservative with calorie estimates - prefer slightly over than under
5. Include helpful notes about portions (e.g., "large serving", "with sauce")
6. Only return valid JSON, no additional text or markdown
7. If you cannot identify any food, return: {{"error": "Could not identify food items"}}
8. For Malaysian/Asian foods, use accurate local calorie estimates
9. Break down combo meals into individual items when possible
"""


class AIFoodLogService:
    """Service for parsing food data using OpenAI GPT-4o."""

    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    def _get_system_prompt(self) -> str:
        """Get system prompt with today's date."""
        return FOOD_LOG_SYSTEM_PROMPT.format(today=date.today().strftime('%Y-%m-%d'))

    def _parse_response(self, response_text: str) -> dict:
        """Parse AI response text into structured data."""
        try:
            data = json.loads(response_text)
            if "error" in data:
                return {"success": False, "error": data["error"]}
            return {"success": True, "data": data}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Failed to parse AI response: {str(e)}"}

    def parse_text_input(self, user_text: str) -> dict:
        """
        Parse natural language food description.

        Args:
            user_text: Natural language description of food eaten

        Returns:
            dict with 'success' boolean and either 'data' or 'error'
        """
        if not user_text or not user_text.strip():
            return {"success": False, "error": "No text provided"}

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": f"Log this food: {user_text}"}
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.3
            )

            response_text = response.choices[0].message.content
            return self._parse_response(response_text)

        except Exception as e:
            return {"success": False, "error": f"AI service error: {str(e)}"}

    def parse_image_input(self, image_data: bytes, content_type: str, context: str = "") -> dict:
        """
        Parse food image using vision capabilities.

        Args:
            image_data: Raw image bytes
            content_type: MIME type (e.g., 'image/jpeg', 'image/png')
            context: Optional additional context about the image

        Returns:
            dict with 'success' boolean and either 'data' or 'error'
        """
        if not image_data:
            return {"success": False, "error": "No image provided"}

        # Validate content type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if content_type not in allowed_types:
            return {"success": False, "error": f"Unsupported image type: {content_type}"}

        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')

            # Build user message with image
            user_content = [
                {
                    "type": "text",
                    "text": f"Identify and log the food in this image.{' Additional context: ' + context if context else ''}"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content_type};base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.3
            )

            response_text = response.choices[0].message.content
            return self._parse_response(response_text)

        except Exception as e:
            return {"success": False, "error": f"AI service error: {str(e)}"}
