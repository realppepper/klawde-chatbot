import tomllib
from google import genai

with open(".streamlit/api.toml", "rb") as f:
    secrets = tomllib.load(f)
API_KEY = secrets["GEMINI_API_KEY"]

client = genai.Client(api_key=API_KEY)

print("사용 가능한 모델 목록:")
for model in client.models.list():
    methods = getattr(model, "supported_actions", None) or getattr(model, "supported_generation_methods", None) or []
    print(f"  {model.name}")
