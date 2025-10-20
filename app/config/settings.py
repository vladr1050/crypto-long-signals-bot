"""
Application configuration settings
"""
import json
import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Bot configuration
    bot_token: str = Field(..., env="BOT_TOKEN")
    
    # Database configuration
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Exchange configuration
    exchange: str = Field(default="binance", env="EXCHANGE")
    binance_api_key: str = Field(default="", env="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", env="BINANCE_API_SECRET")
    
    # Scanning configuration
    scan_interval_sec: int = Field(default=180, env="SCAN_INTERVAL_SEC")
    default_risk_pct: float = Field(default=0.7, env="DEFAULT_RISK_PCT")
    default_pairs: str = Field(
        default="ETH/USDC,BNB/USDC,XRP/USDC,SOL/USDC,ADA/USDC",
        env="DEFAULT_PAIRS"
    )
    
    # Risk management
    max_concurrent_signals: int = 3
    max_holding_hours: int = 24
    min_volume_24h: float = 1000000  # $1M minimum volume
    
    # Signal configuration
    signal_expiry_hours: int = 8
    rsi_period: int = 14
    ema_200_period: int = 200
    ema_50_period: int = 50
    ema_9_period: int = 9
    ema_21_period: int = 21
    bb_period: int = 20
    bb_std: float = 2.0
    atr_period: int = 14
    
    # Timeframes
    trend_timeframe: str = "1h"
    entry_timeframe: str = "15m"
    confirmation_timeframe: str = "5m"
    
    @property
    def pairs_list(self) -> List[str]:
        """Get pairs as list, handling both JSON array and comma-separated string formats"""
        try:
            # Try to parse as JSON array first
            if self.default_pairs.startswith('[') and self.default_pairs.endswith(']'):
                return json.loads(self.default_pairs)
            else:
                # Fall back to comma-separated string
                return [pair.strip() for pair in self.default_pairs.split(",")]
        except (json.JSONDecodeError, AttributeError):
            # If JSON parsing fails, try comma-separated string
            return [pair.strip() for pair in self.default_pairs.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


_settings: Settings = None


def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Create a global settings instance for easier access
settings = get_settings()