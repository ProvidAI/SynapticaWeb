from dotenv import load_dotenv
import os

load_dotenv()  # must be called before using os.getenv

api_key = os.getenv("OPENAI_API_KEY")
print(api_key)  # should print your key
