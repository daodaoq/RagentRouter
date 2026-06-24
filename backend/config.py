from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./ragent_router.db"

    # Demo mode — when True, AI providers return mock responses (no API key needed)
    demo_mode: bool = True

    # Provider API keys (optional in demo mode)
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""

    # Provider base URLs
    anthropic_base_url: str = "https://api.anthropic.com"
    deepseek_base_url: str = "https://api.deepseek.com"

    # Default models
    default_claude_model: str = "claude-sonnet-4-6"
    default_deepseek_model: str = "deepseek-chat"

    # Cost per 1M tokens (USD)
    claude_input_cost_per_m: float = 3.0
    claude_output_cost_per_m: float = 15.0
    deepseek_input_cost_per_m: float = 0.27
    deepseek_output_cost_per_m: float = 1.10

    class Config:
        env_file = ".env"
        env_prefix = "RAGENT_"


settings = Settings()
