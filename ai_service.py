import google.generativeai as genai

from config import GEMINI_API_KEY

# ==================================================
# Configure Gemini
# ==================================================

genai.configure(api_key=GEMINI_API_KEY)

MODEL = genai.GenerativeModel("gemini-2.5-flash")


async def generate_response(prompt: str) -> str:
    """
    Generate a response from Gemini.
    """

    try:
        response = MODEL.generate_content(prompt)

        if response and response.text:
            return response.text

        return "I couldn't generate a response."

    except Exception as e:
        return f"Gemini Error: {e}"
