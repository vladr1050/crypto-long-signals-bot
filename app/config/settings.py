from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    exchange: str = Field(default="binance", alias="EXCHANGE")
    scan_interval_sec: int = Field(default=180, alias="SCAN_INTERVAL_SEC")
    default_risk_pct: float = Field(default=0.7, alias="DEFAULT_RISK_PCT")
    default_pairs: List[str] = Field(
        default=["ETH/USDC", "BNB/USDC", "XRP/USDC", "SOL/USDC", "ADA/USDC"],
        alias="DEFAULT_PAIRS",
    )
    binance_api_key: str | None = Field(default=None, alias="BINANCE_API_KEY")
    binance_api_secret: str | None = Field(default=None, alias="BINANCE_API_SECRET")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
