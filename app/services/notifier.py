"""
Notification service for sending signals via Telegram
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards.common import get_signal_keyboard
from app.bot.texts_en import *
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to users"""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def send_signal(
        self, 
        bot: Bot, 
        user_id: int, 
        signal: Dict,
        db_repo
    ) -> bool:
        """
        Send signal notification to user
        
        Args:
            bot: Telegram bot instance
            user_id: User Telegram ID
            signal: Signal data dictionary
            db_repo: Database repository
            
        Returns:
            True if sent successfully
        """
        try:
            # Check if user wants signals
            user = await db_repo.get_or_create_user(user_id)
            if not user.signals_enabled:
                return False
            
            # Format signal message
            message = self._format_signal_message(signal)
            
            # Create keyboard
            keyboard = get_signal_keyboard(signal.get('id', 0), signal['symbol'])
            
            # Send message
            await bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            logger.info(f"Signal sent to user {user_id}: {signal['symbol']} {signal['grade']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending signal to user {user_id}: {e}")
            return False
    
    def _format_signal_message(self, signal: Dict) -> str:
        """
        Format signal data into message text
        
        Args:
            signal: Signal data dictionary
            
        Returns:
            Formatted message string
        """
        try:
            # Get grade description
            grade_descriptions = {
                "A": GRADE_A,
                "B": GRADE_B, 
                "C": GRADE_C
            }
            grade_desc = grade_descriptions.get(signal['grade'], signal['grade'])
            
            # Calculate percentages
            entry = signal['entry_price']
            sl = signal['stop_loss']
            tp1 = signal['take_profit_1']
            tp2 = signal['take_profit_2']
            
            sl_pct = round(((entry - sl) / entry) * 100, 1)
            tp1_pct = round(((tp1 - entry) / entry) * 100, 1)
            tp2_pct = round(((tp2 - entry) / entry) * 100, 1)
            
            # Calculate position size (mock - would need account value)
            position_size = round(1000 / entry, 4)  # Mock $1000 account
            
            # Build message
            message = SIGNAL_HEADER.format(
                grade=grade_desc,
                symbol=signal['symbol'],
                timeframe=signal['timeframe']
            )
            message += f"\n\n{SIGNAL_ENTRY.format(entry=entry)}"
            message += f"\n{SIGNAL_SL.format(sl=sl, sl_pct=sl_pct)}"
            message += f"\n{SIGNAL_TP1.format(tp1=tp1, tp1_pct=tp1_pct)}"
            message += f"\n{SIGNAL_TP2.format(tp2=tp2, tp2_pct=tp2_pct)}"
            message += f"\n\n{SIGNAL_RISK.format(risk=signal['risk_level'], position=position_size)}"
            message += f"\n\n{SIGNAL_REASON.format(reason=signal['reason'])}"
            message += f"\n\n{SIGNAL_EXPIRY.format(expiry=signal.get('expiry_hours', 8))}"
            message += f"\n\n{SIGNAL_NOTE}"
            message += f"\n\n{SIGNAL_DISCLAIMER}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting signal message: {e}")
            return f"Signal detected for {signal.get('symbol', 'Unknown')}"
    
    async def send_status_update(
        self, 
        bot: Bot, 
        user_id: int, 
        message: str,
        keyboard: InlineKeyboardMarkup = None
    ) -> bool:
        """
        Send status update to user
        
        Args:
            bot: Telegram bot instance
            user_id: User Telegram ID
            message: Status message
            keyboard: Optional keyboard
            
        Returns:
            True if sent successfully
        """
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error sending status update to user {user_id}: {e}")
            return False
    
    async def send_error_notification(
        self, 
        bot: Bot, 
        user_id: int, 
        error_message: str
    ) -> bool:
        """
        Send error notification to user
        
        Args:
            bot: Telegram bot instance
            user_id: User Telegram ID
            error_message: Error message
            
        Returns:
            True if sent successfully
        """
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"❌ <b>Error:</b> {error_message}",
                parse_mode="HTML"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error sending error notification to user {user_id}: {e}")
            return False
    
    async def send_bulk_signals(
        self, 
        bot: Bot, 
        signals: List[Dict],
        db_repo
    ) -> int:
        """
        Send multiple signals to all users
        
        Args:
            bot: Telegram bot instance
            signals: List of signal dictionaries
            db_repo: Database repository
            
        Returns:
            Number of signals sent successfully
        """
        sent_count = 0
        
        try:
            # Get all users who want signals
            # Note: In a real implementation, you'd have a method to get all users
            # For now, we'll just log the signals
            for signal in signals:
                logger.info(f"Signal generated: {signal['symbol']} {signal['grade']}")
                sent_count += 1
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending bulk signals: {e}")
            return sent_count
    
    def format_signal_summary(self, signals: List[Dict]) -> str:
        """
        Format a summary of multiple signals
        
        Args:
            signals: List of signal dictionaries
            
        Returns:
            Formatted summary string
        """
        if not signals:
            return "No signals detected in this scan."
        
        summary = f"📊 <b>Scan Results</b> - {len(signals)} signal(s) detected:\n\n"
        
        for signal in signals:
            grade_emoji = {"A": "🟢", "B": "🟡", "C": "🔴"}.get(signal['grade'], "⚪")
            summary += f"{grade_emoji} {signal['symbol']} - {signal['grade']} grade\n"
        
        return summary