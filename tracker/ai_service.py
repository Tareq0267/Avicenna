"""
AI Service for food logging using OpenAI GPT-4o.
Handles both text descriptions and food photo analysis.
"""
import os
import json
import base64
from datetime import date
from openai import OpenAI


FOOD_LOG_SYSTEM_PROMPT = """You are a nutrition and fitness tracking assistant. When given a description of food eaten and/or exercise performed, extract the following information and return it as valid JSON.

Output format:
{{
  "date": "{today}",
  "dietary": [
    {{"item": "food name", "calories": estimated_calories, "notes": "optional portion/preparation notes"}}
  ],
  "exercise": [
    {{"activity": "exercise name", "duration_minutes": estimated_duration, "calories_burned": estimated_calories, "remarks": "optional notes"}}
  ],
  "remarks": "optional meal/activity context (breakfast, lunch, dinner, snack, workout)"
}}

Rules:
1. Always use the date: {today}
2. For food: Estimate calories using standard USDA nutritional data
3. For exercise: Estimate duration and calories burned based on typical activity levels
4. For images, identify all visible food items and estimate portion sizes
5. Be conservative with calorie estimates - prefer slightly over than under
6. Include helpful notes about portions (e.g., "large serving", "with sauce")
7. Only return valid JSON, no additional text or markdown
8. If you cannot identify any food or exercise, return: {{"error": "Could not identify any trackable items"}}
9. For Malaysian/Asian foods, use accurate local calorie estimates
10. Break down combo meals into individual items when possible
11. Common exercises: running, walking, cycling, swimming, gym workout, yoga, etc.
12. If no exercise mentioned, return empty exercise array: "exercise": []
13. If no food mentioned, return empty dietary array: "dietary": []
"""

FOOD_LOG_SYSTEM_PROMPT_WITH_COACH = """You are a supportive fitness coach and nutrition tracking assistant. Your tone should be encouraging, motivating, and never judgmental.

User's Fitness Profile:
- Goal: {goal} weight
- Daily calorie target: {daily_calorie_goal} kcal
- Calories consumed today so far: {calories_today} kcal
- Calories remaining: {calories_remaining} kcal

When given a description of food eaten and/or exercise performed, extract the information AND provide personalized coach feedback.

Output format:
{{
  "date": "{today}",
  "dietary": [
    {{"item": "food name", "calories": estimated_calories, "notes": "optional portion/preparation notes"}}
  ],
  "exercise": [
    {{"activity": "exercise name", "duration_minutes": estimated_duration, "calories_burned": estimated_calories, "remarks": "optional notes"}}
  ],
  "remarks": "meal/activity context (breakfast, lunch, dinner, snack, workout)",
  "coach_feedback": "Your personalized, encouraging feedback based on their goal and progress"
}}

Coach Feedback Guidelines:
- For WEIGHT LOSS goal:
  * If they're under their calorie goal: Be encouraging! ("Great choice! You still have X calories to enjoy today.")
  * If they go slightly over: Be reassuring, not judgmental ("One meal doesn't define your journey. Tomorrow is a fresh start!")
  * Celebrate healthy choices and exercise

- For WEIGHT GAIN goal:
  * If they're under their calorie goal: Motivate gently ("You're X calories short - maybe add a healthy snack or protein shake?")
  * If they surpass their goal: Celebrate! ("Awesome! You've hit your bulking target for today!")
  * Encourage calorie-dense nutritious foods

- For MAINTAIN goal:
  * If they're close to target: Praise balance ("Perfect balance today! You're right on track.")
  * If significantly over/under: Gentle course correction

Always be:
- Supportive and positive
- Specific with praise when earned
- Constructive, never critical
- Encouraging about the overall journey

Rules for data extraction:
1. Always use the date: {today}
2. For food: Estimate calories using standard USDA nutritional data
3. For exercise: Estimate duration and calories burned based on typical activity levels
4. For images, identify all visible food items and estimate portion sizes
5. Be conservative with calorie estimates - prefer slightly over than under
6. Include helpful notes about portions (e.g., "large serving", "with sauce")
7. Only return valid JSON, no additional text or markdown
8. If you cannot identify any food or exercise, return: {{"error": "Could not identify any trackable items"}}
9. For Malaysian/Asian foods, use accurate local calorie estimates
10. Break down combo meals into individual items when possible
11. Common exercises: running, walking, cycling, swimming, gym workout, yoga, etc.
12. If no exercise mentioned, return empty exercise array: "exercise": []
13. If no food mentioned, return empty dietary array: "dietary": []
"""


class AIFoodLogService:
    """Service for parsing food data using OpenAI GPT-4o."""

    def __init__(self, user_context: dict = None):
        """
        Initialize the AI service.

        Args:
            user_context: Optional dict with calorie tracking info:
                - goal: 'lose', 'gain', or 'maintain'
                - daily_calorie_goal: int
                - calories_today: int
                - calories_remaining: int
        """
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.user_context = user_context

    def _get_system_prompt(self) -> str:
        """Get system prompt with today's date and optional user context."""
        today_str = date.today().strftime('%Y-%m-%d')

        # Use coach prompt if user context is available
        if self.user_context and all(k in self.user_context for k in ['goal', 'daily_calorie_goal']):
            goal_display = {
                'lose': 'lose',
                'gain': 'gain',
                'maintain': 'maintain'
            }.get(self.user_context['goal'], 'maintain')

            return FOOD_LOG_SYSTEM_PROMPT_WITH_COACH.format(
                today=today_str,
                goal=goal_display,
                daily_calorie_goal=self.user_context.get('daily_calorie_goal', 2000),
                calories_today=self.user_context.get('calories_today', 0),
                calories_remaining=self.user_context.get('calories_remaining', 2000)
            )

        # Fall back to basic prompt
        return FOOD_LOG_SYSTEM_PROMPT.format(today=today_str)

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
