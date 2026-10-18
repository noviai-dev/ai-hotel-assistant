import os
from dotenv import load_dotenv

# 加载 .env 文件到环境变量中
load_dotenv()

class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/hotel_assistant")
        self.secret_key = os.getenv("SECRET_KEY", "your_default_secret_key")
        self.debug_mode = os.getenv("DEBUG", "False").lower() == "true"

        self.data_collection_sources = os.getenv("DATA_COLLECTION_SOURCES", "booking")
        self.data_collection_sources_list = [source.strip() for source in self.data_collection_sources.split(",") if source.strip()]
        self.data_collection_api_key = os.getenv("DATA_COLLECTION_API_KEY", "your_api_key_here")
        self.data_collection_api_secret = os.getenv("DATA_COLLECTION_API_SECRET", "your_api_secret_here")


settings = Settings()
