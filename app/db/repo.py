"""
Database repository for Crypto Long Signals Bot
"""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings
from app.db.models import Base, Pair, Setting, Signal, SignalStatus, User


class DatabaseRepository:
    """Database repository for managing data operations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def initialize(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Initialize default pairs
        await self._initialize_default_pairs()
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()
    
    async def _initialize_default_pairs(self):
        """Initialize default trading pairs"""
        settings = get_settings()
        async with self.async_session() as session:
            for symbol in settings.pairs_list:
                # Check if pair already exists
                result = await session.execute(
                    select(Pair).where(Pair.symbol == symbol)
                )
                if not result.scalar_one_or_none():
                    pair = Pair(symbol=symbol, enabled=True)
                    session.add(pair)
            await session.commit()
    
    # User operations
    async def get_or_create_user(self, tg_id: int) -> User:
        """Get or create user by Telegram ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.tg_id == tg_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(tg_id=tg_id)
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            return user
    
    async def update_user_risk(self, tg_id: int, risk_pct: float) -> bool:
        """Update user risk percentage"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.tg_id == tg_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.risk_pct = risk_pct
                user.updated_at = datetime.utcnow()
                await session.commit()
                return True
            return False
    
    async def toggle_user_signals(self, tg_id: int) -> bool:
        """Toggle user signals on/off"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.tg_id == tg_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.signals_enabled = not user.signals_enabled
                user.updated_at = datetime.utcnow()
                await session.commit()
                return user.signals_enabled
            return False
    
    # Pair operations
    async def get_enabled_pairs(self) -> List[Pair]:
        """Get all enabled trading pairs"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Pair).where(Pair.enabled == True)
            )
            return result.scalars().all()
    
    async def get_all_pairs(self) -> List[Pair]:
        """Get all trading pairs"""
        async with self.async_session() as session:
            result = await session.execute(select(Pair))
            return result.scalars().all()
    
    async def toggle_pair(self, symbol: str) -> bool:
        """Toggle pair enabled status"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Pair).where(Pair.symbol == symbol)
            )
            pair = result.scalar_one_or_none()
            
            if pair:
                pair.enabled = not pair.enabled
                await session.commit()
                return pair.enabled
            return False
    
    async def add_pair(self, symbol: str) -> bool:
        """Add new trading pair"""
        async with self.async_session() as session:
            # Check if pair already exists
            result = await session.execute(
                select(Pair).where(Pair.symbol == symbol)
            )
            if result.scalar_one_or_none():
                return False
            
            pair = Pair(symbol=symbol, enabled=True)
            session.add(pair)
            await session.commit()
            return True
    
    # Signal operations
    async def create_signal(
        self,
        symbol: str,
        timeframe: str,
        entry_price: float,
        stop_loss: float,
        take_profit_1: float,
        take_profit_2: float,
        grade: str,
        risk_level: float,
        reason: str,
        expires_at: datetime
    ) -> Signal:
        """Create new signal"""
        async with self.async_session() as session:
            signal = Signal(
                symbol=symbol,
                timeframe=timeframe,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
                grade=grade,
                risk_level=risk_level,
                reason=reason,
                expires_at=expires_at
            )
            session.add(signal)
            await session.commit()
            await session.refresh(signal)
            return signal
    
    async def get_active_signals(self) -> List[Signal]:
        """Get all active signals"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Signal).where(
                    and_(
                        Signal.status == SignalStatus.ACTIVE,
                        Signal.expires_at > datetime.utcnow()
                    )
                )
            )
            return result.scalars().all()
    
    async def get_user_signals(self, tg_id: int) -> List[Signal]:
        """Get signals for specific user (mock implementation)"""
        # In a real implementation, you'd link signals to users
        # For now, return all active signals
        return await self.get_active_signals()
    
    async def expire_old_signals(self):
        """Expire signals that are past their expiry time"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Signal).where(
                    and_(
                        Signal.status == SignalStatus.ACTIVE,
                        Signal.expires_at <= datetime.utcnow()
                    )
                )
            )
            signals = result.scalars().all()
            
            for signal in signals:
                signal.status = SignalStatus.EXPIRED
                signal.updated_at = datetime.utcnow()
            
            await session.commit()
            return len(signals)
    
    async def get_signals_count(self) -> int:
        """Get count of active signals"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Signal).where(Signal.status == SignalStatus.ACTIVE)
            )
            return len(result.scalars().all())
    
    # Settings operations
    async def get_setting(self, key: str) -> Optional[str]:
        """Get setting value by key"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == key)
            )
            setting = result.scalar_one_or_none()
            return setting.value if setting else None
    
    async def set_setting(self, key: str, value: str) -> bool:
        """Set setting value"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = Setting(key=key, value=value)
                session.add(setting)
            
            await session.commit()
            return True
    
    async def get_users_with_signals_enabled(self) -> List[User]:
        """Get all users who have signals enabled"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(User).where(User.signals_enabled == True)
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting users with signals enabled: {e}")
            return []
    
    async def get_signal_by_id(self, signal_id: int) -> Optional[Signal]:
        """Get signal by ID"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Signal).where(Signal.id == signal_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting signal by ID {signal_id}: {e}")
            return None
    
    async def update_signal_status(self, signal_id: int, status: str) -> bool:
        """Update signal status"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Signal).where(Signal.id == signal_id)
                )
                signal = result.scalar_one_or_none()
                
                if signal:
                    signal.status = status
                    signal.updated_at = datetime.utcnow()
                    await session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating signal status {signal_id}: {e}")
            return False
    
    async def snooze_signal(self, signal_id: int, snooze_until: datetime) -> bool:
        """Snooze signal until specified time"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Signal).where(Signal.id == signal_id)
                )
                signal = result.scalar_one_or_none()
                
                if signal:
                    # Store original expiry time and set new expiry
                    signal.snooze_until = snooze_until
                    signal.updated_at = datetime.utcnow()
                    await session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error snoozing signal {signal_id}: {e}")
            return False
    
    async def get_active_signals_count(self) -> int:
        """Get count of all active signals"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(func.count(Signal.id)).where(Signal.status == "active")
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting active signals count: {e}")
            return 0
    
    async def get_user_active_signals_count(self, user_id: int) -> int:
        """Get count of signals marked as active by specific user"""
        try:
            # For now, we'll count all active signals since we don't track user ownership
            # In a more advanced version, we'd track which user marked which signal as active
            async with self.async_session() as session:
                result = await session.execute(
                    select(func.count(Signal.id)).where(Signal.status == "active")
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting user active signals count: {e}")
            return 0
    
    async def add_snooze_column_if_not_exists(self) -> bool:
        """Add snooze_until column to signals table if it doesn't exist"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with self.async_session() as session:
                # Check if column exists
                result = await session.execute(
                    text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'signals' 
                        AND column_name = 'snooze_until'
                    """)
                )
                column_exists = result.fetchone() is not None
                
                if not column_exists:
                    # Add the column
                    await session.execute(
                        text("ALTER TABLE signals ADD COLUMN snooze_until TIMESTAMP")
                    )
                    await session.commit()
                    logger.info("✅ Added snooze_until column to signals table")
                    return True
                else:
                    logger.info("✅ snooze_until column already exists")
                    return True
        except Exception as e:
            logger.error(f"Error adding snooze_until column: {e}")
            return False