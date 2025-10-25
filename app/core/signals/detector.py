"""
Signal detection logic for crypto long signals
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.core.indicators.ta import TechnicalAnalysis
from app.core.risk.sizing import RiskManager
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class SignalDetector:
    """Signal detection engine for long positions only"""
    
    def __init__(self, ta: TechnicalAnalysis, risk_manager: RiskManager):
        self.ta = ta
        self.risk_manager = risk_manager
        self.settings = get_settings()
    
    def detect_signals(
        self, 
        market_data: Dict[str, Dict[str, pd.DataFrame]],
        user_risk_pct: float = None
    ) -> List[Dict]:
        """
        Detect long signals across all symbols and timeframes
        
        Args:
            market_data: Nested dict of {symbol: {timeframe: DataFrame}}
            user_risk_pct: User's risk percentage (overrides default)
            
        Returns:
            List of detected signals
        """
        signals = []
        
        for symbol, timeframes in market_data.items():
            try:
                signal = self._detect_signal_for_symbol(symbol, timeframes, user_risk_pct)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error detecting signal for {symbol}: {e}")
        
        return signals
    
    def _detect_signal_for_symbol(
        self, 
        symbol: str, 
        timeframes: Dict[str, pd.DataFrame],
        user_risk_pct: float = None
    ) -> Optional[Dict]:
        """
        Detect signal for a specific symbol
        
        Args:
            symbol: Trading pair symbol
            timeframes: Dict of {timeframe: DataFrame}
            
        Returns:
            Signal dict or None if no signal
        """
        try:
            # Get required timeframes
            trend_df = timeframes.get(self.settings.trend_timeframe)
            entry_df = timeframes.get(self.settings.entry_timeframe)
            confirmation_df = timeframes.get(self.settings.confirmation_timeframe)
            
            if not all([trend_df is not None, entry_df is not None, confirmation_df is not None]):
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Check minimum data requirements
            if len(trend_df) < 200 or len(entry_df) < 50 or len(confirmation_df) < 20:
                logger.warning(f"Insufficient data length for {symbol}")
                return None
            
            # Apply trend filter (must pass)
            if not self._check_trend_filter(trend_df, entry_df):
                return None
            
            # Check entry triggers (need at least 2)
            triggers = self._check_entry_triggers(entry_df, confirmation_df)
            if len(triggers) < 2:
                return None
            
            # Calculate signal parameters
            entry_price = entry_df['close'].iloc[-1]
            stop_loss = self.ta.calculate_stop_loss(entry_df, entry_price)
            
            # Validate risk parameters
            risk_pct = user_risk_pct if user_risk_pct is not None else self.settings.default_risk_pct
            is_valid, error_msg = self.risk_manager.validate_risk_parameters(
                risk_pct, entry_price, stop_loss
            )
            
            if not is_valid:
                logger.warning(f"Invalid risk parameters for {symbol}: {error_msg}")
                return None
            
            # Calculate take profits
            tp1, tp2 = self.risk_manager.calculate_take_profits(entry_price, stop_loss, risk_pct)
            
            # Calculate signal grade
            grade = self._calculate_signal_grade(triggers, entry_df, confirmation_df)
            
            # Calculate risk-reward ratio
            risk_reward = self.risk_manager.calculate_risk_reward_ratio(
                entry_price, stop_loss, tp1
            )
            
            # Create signal
            signal = {
                'symbol': symbol,
                'timeframe': self.settings.entry_timeframe,
                'entry_price': round(entry_price, 6),
                'stop_loss': round(stop_loss, 6),
                'take_profit_1': round(tp1, 6),
                'take_profit_2': round(tp2, 6),
                'grade': grade,
                'risk_level': risk_pct,
                'risk_reward_ratio': round(risk_reward, 2),
                'reason': self._generate_signal_reason(triggers, grade),
                'triggers': triggers,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=self.settings.signal_expiry_hours)
            }
            
            logger.info(f"Signal detected for {symbol}: {grade} grade, {risk_reward:.2f} R/R")
            return signal
            
        except Exception as e:
            logger.error(f"Error detecting signal for {symbol}: {e}")
            return None
    
    def _check_trend_filter(self, trend_df: pd.DataFrame, entry_df: pd.DataFrame) -> bool:
        """
        Check if trend filter conditions are met (must pass)
        
        Args:
            trend_df: 1h timeframe data for trend analysis
            entry_df: 15m timeframe data for entry analysis
            
        Returns:
            True if trend filter passes
        """
        try:
            # Check 1h trend (price > EMA200)
            trend_bullish = self.ta.is_trend_bullish(trend_df)
            
            # Check 15m trend (price > EMA50)
            entry_trend_bullish = self.ta.is_trend_bullish(entry_df)
            
            # Check RSI in neutral to slightly bullish range
            rsi_neutral = self.ta.is_rsi_neutral_bullish(trend_df)
            
            # For debugging: log the individual conditions
            logger.debug(f"Trend filter: 1h_bullish={trend_bullish}, 15m_bullish={entry_trend_bullish}, rsi_neutral={rsi_neutral}")
            
            return trend_bullish and entry_trend_bullish and rsi_neutral
            
        except Exception as e:
            logger.error(f"Error checking trend filter: {e}")
            return False
    
    def _check_entry_triggers(
        self, 
        entry_df: pd.DataFrame, 
        confirmation_df: pd.DataFrame
    ) -> List[str]:
        """
        Check entry trigger conditions (need at least 2)
        
        Args:
            entry_df: 15m timeframe data
            confirmation_df: 5m timeframe data
            
        Returns:
            List of triggered conditions
        """
        triggers = []
        
        try:
            # 1. Breakout & retest of local resistance
            if self.ta.check_breakout_retest(entry_df):
                triggers.append("breakout_retest")
            
            # 2. Bollinger Bands squeeze expansion + volume
            if self.ta.check_bollinger_squeeze_expansion(entry_df):
                triggers.append("bb_squeeze_expansion")
            
            # 3. EMA9/EMA21 bullish crossover above EMA50
            if self.ta.check_ema_crossover(entry_df):
                triggers.append("ema_crossover")
            
            # 4. Bullish candle with volume confirmation
            if self.ta.check_bullish_candle(confirmation_df):
                triggers.append("bullish_candle")
            
        except Exception as e:
            logger.error(f"Error checking entry triggers: {e}")
        
        return triggers
    
    def _calculate_signal_grade(
        self, 
        triggers: List[str], 
        entry_df: pd.DataFrame, 
        confirmation_df: pd.DataFrame
    ) -> str:
        """
        Calculate signal grade based on triggers and market conditions
        
        Args:
            triggers: List of triggered conditions
            entry_df: Entry timeframe data
            confirmation_df: Confirmation timeframe data
            
        Returns:
            Signal grade (A, B, or C)
        """
        try:
            # Count triggers (more triggers = higher grade)
            trigger_count = len(triggers)
            
            # Check trend strength
            trend_strength = 1
            if self.ta.is_trend_bullish(entry_df):
                trend_strength = 2
                if self.ta.is_trend_bullish(confirmation_df):
                    trend_strength = 3
            
            # Check volume confirmation
            volume_confirmation = False
            try:
                volume_sma = self.ta.calculate_volume_sma(entry_df['volume'])
                current_volume = entry_df['volume'].iloc[-1]
                avg_volume = volume_sma.iloc[-1]
                volume_confirmation = current_volume > avg_volume * 1.2
            except:
                pass
            
            # Check pattern quality
            pattern_quality = 1
            if trigger_count >= 3:
                pattern_quality = 3
            elif trigger_count >= 2:
                pattern_quality = 2
            
            # Calculate risk-reward ratio
            entry_price = entry_df['close'].iloc[-1]
            stop_loss = self.ta.calculate_stop_loss(entry_df, entry_price)
            tp1, _ = self.risk_manager.calculate_take_profits(entry_price, stop_loss)
            risk_reward = self.risk_manager.calculate_risk_reward_ratio(
                entry_price, stop_loss, tp1
            )
            
            return self.risk_manager.calculate_signal_grade(
                trend_strength, volume_confirmation, pattern_quality, risk_reward
            )
            
        except Exception as e:
            logger.error(f"Error calculating signal grade: {e}")
            return "C"
    
    def _generate_signal_reason(self, triggers: List[str], grade: str) -> str:
        """
        Generate human-readable signal reason
        
        Args:
            triggers: List of triggered conditions
            grade: Signal grade
            
        Returns:
            Signal reason string
        """
        try:
            trigger_descriptions = {
                "breakout_retest": "Breakout & retest of resistance",
                "bb_squeeze_expansion": "BB squeeze expansion + volume",
                "ema_crossover": "EMA crossover above EMA50",
                "bullish_candle": "Bullish candle + volume"
            }
            
            trigger_texts = [trigger_descriptions.get(t, t) for t in triggers]
            
            grade_descriptions = {
                "A": "Strong setup",
                "B": "Good setup", 
                "C": "High-risk setup"
            }
            
            grade_text = grade_descriptions.get(grade, "Unknown grade")
            
            if len(trigger_texts) == 1:
                reason = f"{grade_text}: {trigger_texts[0]}"
            else:
                reason = f"{grade_text}: {', '.join(trigger_texts[:-1])} and {trigger_texts[-1]}"
            
            return reason
            
        except Exception as e:
            logger.error(f"Error generating signal reason: {e}")
            return f"{grade} grade signal detected"
    
    def should_generate_signal(self, symbol: str, current_signals: List[Dict]) -> bool:
        """
        Check if we should generate a new signal for this symbol
        
        Args:
            symbol: Trading pair symbol
            current_signals: List of current active signals
            
        Returns:
            True if we should generate a new signal
        """
        try:
            # Check max concurrent signals
            if len(current_signals) >= self.settings.max_concurrent_signals:
                return False
            
            # Check if symbol already has an active signal
            for signal in current_signals:
                if signal.get('symbol') == symbol:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal generation: {e}")
            return False