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
    
    def calculate_adaptive_position_size(
        self, 
        account_value: float, 
        user_risk_pct: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """
        Calculate position size based on user's risk percentage and real market risk
        
        Args:
            account_value: Total account value
            user_risk_pct: User's desired risk percentage
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size in base currency
        """
        try:
            if entry_price <= stop_loss:
                logger.warning("Entry price must be greater than stop loss")
                return 0.0
            
            # Calculate real market risk percentage
            real_risk_pct = ((entry_price - stop_loss) / entry_price) * 100
            
            # Calculate how much of user's risk we can use
            risk_multiplier = user_risk_pct / real_risk_pct
            
            # Calculate position size
            position_value = account_value * risk_multiplier
            position_size = position_value / entry_price
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating adaptive position size: {e}")
            return 0.0
    
    def calculate_take_profits(self, entry_price: float, stop_loss: float, tp1: float = None, tp2: float = None) -> Tuple[float, float]:
        """
        Use technical analysis take profits or fallback to 1R/2R logic
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            tp1: Technical analysis TP1 (if provided)
            tp2: Technical analysis TP2 (if provided)
            
        Returns:
            Tuple of (TP1, TP2) prices
        """
        try:
            if entry_price <= stop_loss:
                logger.warning("Entry price must be greater than stop loss")
                return entry_price, entry_price
            
            if tp1 is not None and tp2 is not None:
                # Use technical analysis take profits
                return tp1, tp2
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
        stop_loss: float,
        is_easy_mode: bool = False
    ) -> Tuple[bool, str]:
        """
        Validate risk parameters
        
        Args:
            risk_per_trade: Risk percentage per trade
            entry_price: Entry price
            stop_loss: Stop loss price
            is_easy_mode: Whether this is Easy Mode (more lenient validation)
            
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
            
            # Check stop loss distance (more lenient for Easy Mode)
            stop_loss_pct = ((entry_price - stop_loss) / entry_price) * 100
            min_distance = 0.3 if is_easy_mode else 0.5  # 0.3% for Easy Mode, 0.5% for Conservative
            max_distance = 15.0 if is_easy_mode else 10.0  # 15% for Easy Mode, 10% for Conservative
            
            if stop_loss_pct < min_distance:
                mode_text = "Easy Mode" if is_easy_mode else "Conservative Mode"
                return False, f"Stop loss too close to entry (< {min_distance}% for {mode_text})"
            if stop_loss_pct > max_distance:
                mode_text = "Easy Mode" if is_easy_mode else "Conservative Mode"
                return False, f"Stop loss too far from entry (> {max_distance}% for {mode_text})"
            
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