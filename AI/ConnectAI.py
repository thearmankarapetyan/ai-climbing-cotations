import os
import openai
from dotenv import load_dotenv

class ConnectAI:
    def __init__(self):
        # Load environment variables from .env (if any)
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY missing")

        # Set the global API key for openai
        openai.api_key = api_key

        # Optionally, store a reference to openai as 'client'
        self.client = openai
 
