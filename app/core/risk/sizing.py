"""
Risk management and position sizing calculations
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class RiskManager:
    """Risk management and position sizing calculations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.max_concurrent_signals = self.settings.max_concurrent_signals
        self.max_holding_hours = self.settings.max_holding_hours
    
    def calculate_position_size(
        self, 
        account_value: float, 
        risk_per_trade: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """
        Calculate position size based on risk percentage
        
        Args:
            account_value: Total account value
            risk_per_trade: Risk percentage per trade (0.01 = 1%)
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size in base currency
        """
        try:
            if entry_price <= stop_loss:
                logger.warning("Entry price must be greater than stop loss")
                return 0.0
            
            # Calculate risk amount
            risk_amount = account_value * (risk_per_trade / 100)
            
            # Calculate risk per unit
            risk_per_unit = entry_price - stop_loss
            
            # Calculate position size
            position_size = risk_amount / risk_per_unit
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def calculate_take_profits(self, entry_price: float, stop_loss: float, risk_pct: float = None) -> Tuple[float, float]:
        """
        Calculate take profit levels based on user's risk percentage
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_pct: User's risk percentage (if None, uses 1R/2R logic)
            
        Returns:
            Tuple of (TP1, TP2) prices
        """
        try:
            if entry_price <= stop_loss:
                logger.warning("Entry price must be greater than stop loss")
                return entry_price, entry_price
            
            if risk_pct is not None:
                # Calculate TP1 and TP2 based on user's risk percentage
                tp1_pct = risk_pct  # TP1 = same as risk
                tp2_pct = risk_pct * 2  # TP2 = 2x risk
                
                tp1 = entry_price * (1 + tp1_pct / 100)
                tp2 = entry_price * (1 + tp2_pct / 100)
            else:
                # Fallback to 1R/2R logic
                risk = entry_price - stop_loss
                tp1 = entry_price + risk  # 1R
                tp2 = entry_price + (2 * risk)  # 2R
            
            return tp1, tp2
            
        except Exception as e:
            logger.error(f"Error calculating take profits: {e}")
            return entry_price, entry_price
    
    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, take_profit: float) -> float:
        """
        Calculate risk-reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Risk-reward ratio
        """
        try:
            if entry_price <= stop_loss:
                return 0.0
            
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
            
            if risk <= 0:
                return 0.0
            
            return reward / risk
            
        except Exception as e:
            logger.error(f"Error calculating risk-reward ratio: {e}")
            return 0.0
    
    def validate_risk_parameters(
        self, 
        risk_per_trade: float, 
        entry_price: float, 
        stop_loss: float
    ) -> Tuple[bool, str]:
        """
        Validate risk parameters
        
        Args:
            risk_per_trade: Risk percentage per trade
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check risk percentage
            if risk_per_trade <= 0 or risk_per_trade > 5.0:
                return False, "Risk per trade must be between 0.1% and 5.0%"
            
            # Check entry and stop loss
            if entry_price <= 0 or stop_loss <= 0:
                return False, "Entry and stop loss must be positive"
            
            if entry_price <= stop_loss:
                return False, "Entry price must be greater than stop loss"
            
            # Check stop loss distance
            stop_loss_pct = ((entry_price - stop_loss) / entry_price) * 100
            if stop_loss_pct < 0.5:
                return False, "Stop loss too close to entry (< 0.5%)"
            if stop_loss_pct > 10.0:
                return False, "Stop loss too far from entry (> 10%)"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating risk parameters: {e}")
            return False, f"Validation error: {e}"
    
    def calculate_signal_grade(
        self, 
        trend_strength: int, 
        volume_confirmation: bool, 
        pattern_quality: int,
        risk_reward_ratio: float
    ) -> str:
        """
        Calculate signal grade based on multiple factors
        
        Args:
            trend_strength: Trend strength score (1-3)
            volume_confirmation: Whether volume confirms the signal
            pattern_quality: Pattern quality score (1-3)
            risk_reward_ratio: Risk-reward ratio
            
        Returns:
            Signal grade (A, B, or C)
        """
        try:
            score = 0
            
            # Trend strength (0-3 points)
            score += trend_strength
            
            # Volume confirmation (0-1 point)
            if volume_confirmation:
                score += 1
            
            # Pattern quality (0-3 points)
            score += pattern_quality
            
            # Risk-reward ratio bonus (0-1 point)
            if risk_reward_ratio >= 2.0:
                score += 1
            elif risk_reward_ratio >= 1.5:
                score += 0.5
            
            # Determine grade
            if score >= 6:
                return "A"  # Strong
            elif score >= 4:
                return "B"  # Good
            else:
                return "C"  # High-risk
                
        except Exception as e:
            logger.error(f"Error calculating signal grade: {e}")
            return "C"
    
    def calculate_signal_expiry(self, signal_created_at: datetime) -> datetime:
        """
        Calculate signal expiry time
        
        Args:
            signal_created_at: When the signal was created
            
        Returns:
            Expiry datetime
        """
        try:
            expiry_hours = self.settings.signal_expiry_hours
            return signal_created_at + timedelta(hours=expiry_hours)
            
        except Exception as e:
            logger.error(f"Error calculating signal expiry: {e}")
            return signal_created_at + timedelta(hours=8)
    
    def should_expire_signal(self, signal_created_at: datetime) -> bool:
        """
        Check if signal should be expired
        
        Args:
            signal_created_at: When the signal was created
            
        Returns:
            True if signal should be expired
        """
        try:
            now = datetime.utcnow()
            max_age = timedelta(hours=self.max_holding_hours)
            return now - signal_created_at > max_age
            
        except Exception as e:
            logger.error(f"Error checking signal expiry: {e}")
            return True
    
    def get_risk_level_description(self, grade: str) -> str:
        """
        Get human-readable risk level description
        
        Args:
            grade: Signal grade (A, B, C)
            
        Returns:
            Risk level description
        """
        descriptions = {
            "A": "Strong - High probability setup with clear trend and volume confirmation",
            "B": "Good - Decent setup with average confirmation signals",
            "C": "High-risk - Weak confirmation or wide stop loss, use smaller position"
        }
        return descriptions.get(grade, "Unknown risk level")
    
    def calculate_max_position_value(
        self, 
        account_value: float, 
        risk_per_trade: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """
        Calculate maximum position value based on risk
        
        Args:
            account_value: Total account value
            risk_per_trade: Risk percentage per trade
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Maximum position value in quote currency
        """
        try:
            position_size = self.calculate_position_size(
                account_value, risk_per_trade, entry_price, stop_loss
            )
            return position_size * entry_price
            
        except Exception as e:
            logger.error(f"Error calculating max position value: {e}")
            return 0.0