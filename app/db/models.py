"""
Database models for Crypto Long Signals Bot
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, Integer, 
    String, Text, create_engine
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class SignalStatus(str, Enum):
    """Signal status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignalGrade(str, Enum):
    """Signal grade enumeration"""
    A = "A"  # Strong
    B = "B"  # Good
    C = "C"  # High-risk


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True, nullable=False)
    lang = Column(String(5), default="en")
    risk_pct = Column(Float, default=0.7)
    signals_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Pair(Base):
    """Trading pair model"""
    __tablename__ = "pairs"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    enabled = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)


class Signal(Base):
    """Signal model"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    grade = Column(String(1), nullable=False)  # A, B, C
    risk_level = Column(Float, nullable=False)  # Risk percentage
    reason = Column(Text, nullable=True)
    status = Column(String(20), default=SignalStatus.PENDING)
    expires_at = Column(DateTime, nullable=False)
    triggered_at = Column(DateTime, nullable=True)
    snooze_until = Column(DateTime, nullable=True)  # For snooze functionality
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Setting(Base):
    """Application settings model"""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)