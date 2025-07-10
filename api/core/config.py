from pydantic_settings import BaseSettings
import dotenv

dotenv.load_dotenv()

class Settings(BaseSettings):
    AUTH_KEY: str
    OPENAI_API_KEY: str
    OPENROUTER_API_KEY: str
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Cache configuration
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 1 hour default TTL
    AUTH_CACHE_TTL: int = 300  # 5 minutes for auth cache
    
    # API Configuration
    API_TITLE: str = "LeaderOracle API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "AI-powered leadership and geopolitical analysis API"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Model Configuration
    MODEL_DIR: str = "/workspace/model"
    MAX_GENERATION_LENGTH: int = 512
    DEFAULT_TEMPERATURE: float = 0.3
    
    # Performance
    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 300  # 5 minutes

    class Config:
        env_file = ".env"

settings = Settings()