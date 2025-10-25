"""
Easy signal detection logic for testing - more lenient conditions
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.core.indicators.ta import TechnicalAnalysis
from app.core.risk.sizing import RiskManager
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class EasySignalDetector:
    """Easy signal detection engine with more lenient conditions for testing"""
    
    def __init__(self, ta: TechnicalAnalysis, risk_manager: RiskManager):
        self.ta = ta
        self.risk_manager = risk_manager
        self.settings = get_settings()
    
    def detect_signals(
        self, 
        market_data: Dict[str, Dict[str, pd.DataFrame]]
    ) -> List[Dict]:
        """
        Detect long signals with easier conditions
        
        Args:
            market_data: Nested dict of {symbol: {timeframe: DataFrame}}
            
        Returns:
            List of detected signals
        """
        signals = []
        
        for symbol, timeframes in market_data.items():
            try:
                signal = self._detect_signal_for_symbol(symbol, timeframes)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error detecting easy signal for {symbol}: {e}")
        
        return signals
    
    def _detect_signal_for_symbol(
        self, 
        symbol: str, 
        timeframes: Dict[str, pd.DataFrame]
    ) -> Optional[Dict]:
        """
        Detect signal for a specific symbol with easier conditions
        
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
            
            # Apply EASY trend filter (only need price > EMA50 on 15m)
            if not self._check_easy_trend_filter(entry_df):
                return None
            
            # Check entry triggers (need at least 1 instead of 2)
            triggers = self._check_easy_entry_triggers(entry_df, confirmation_df)
            if len(triggers) < 1:  # Changed from 2 to 1
                return None
            
            # Calculate signal parameters
            entry_price = entry_df['close'].iloc[-1]
            stop_loss = self.ta.calculate_stop_loss(entry_df, entry_price)
            
            # Validate risk parameters
            risk_pct = self.settings.default_risk_pct
            is_valid, error_msg = self.risk_manager.validate_risk_parameters(
                risk_pct, entry_price, stop_loss
            )
            
            if not is_valid:
                logger.warning(f"Invalid risk parameters for {symbol}: {error_msg}")
                return None
            
            # Calculate take profits
            tp1, tp2 = self.risk_manager.calculate_take_profits(entry_price, stop_loss)
            
            # Calculate signal grade (always B for easy signals)
            grade = "B"
            
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
                'reason': self._generate_easy_signal_reason(triggers),
                'triggers': triggers,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=self.settings.signal_expiry_hours)
            }
            
            logger.info(f"Easy signal detected for {symbol}: {grade} grade, {risk_reward:.2f} R/R")
            return signal
            
        except Exception as e:
            logger.error(f"Error detecting easy signal for {symbol}: {e}")
            return None
    
    def _check_easy_trend_filter(self, entry_df: pd.DataFrame) -> bool:
        """
        Check easy trend filter (NO trend filter - always pass)
        
        Args:
            entry_df: 15m timeframe data
            
        Returns:
            True if easy trend filter passes (always True for testing)
        """
        try:
            # For testing: NO trend filter - always pass
            # This should generate many more signals for testing
            logger.debug("Easy trend filter: ALWAYS PASS (no trend filter for testing)")
            return True
            
        except Exception as e:
            logger.error(f"Error checking easy trend filter: {e}")
            return False
    
    def _check_easy_entry_triggers(
        self, 
        entry_df: pd.DataFrame, 
        confirmation_df: pd.DataFrame
    ) -> List[str]:
        """
        Check easy entry trigger conditions (need at least 1)
        
        Args:
            entry_df: 15m timeframe data
            confirmation_df: 5m timeframe data
            
        Returns:
            List of triggered conditions
        """
        triggers = []
        
        try:
            # 1. EMA9/EMA21 bullish crossover (easier condition)
            if self._check_easy_ema_crossover(entry_df):
                triggers.append("easy_ema_crossover")
            
            # 2. Price above EMA9 (simple momentum)
            if self._check_price_above_ema9(entry_df):
                triggers.append("price_above_ema9")
            
            # 3. Volume increase (simplified)
            if self._check_volume_increase(entry_df):
                triggers.append("volume_increase")
            
            # 4. Bullish candle (any bullish candle)
            if self._check_any_bullish_candle(confirmation_df):
                triggers.append("bullish_candle")
            
        except Exception as e:
            logger.error(f"Error checking easy entry triggers: {e}")
        
        return triggers
    
    def _check_easy_ema_crossover(self, df: pd.DataFrame) -> bool:
        """Check for EMA9/EMA21 crossover (easier condition)"""
        try:
            if len(df) < max(self.settings.ema_9_period, self.settings.ema_21_period):
                return False
            
            ema_9 = self.ta.calculate_ema(df['close'], self.settings.ema_9_period)
            ema_21 = self.ta.calculate_ema(df['close'], self.settings.ema_21_period)
            
            current_ema_9 = ema_9.iloc[-1]
            current_ema_21 = ema_21.iloc[-1]
            prev_ema_9 = ema_9.iloc[-2]
            prev_ema_21 = ema_21.iloc[-2]
            
            # Crossover: EMA9 crosses above EMA21
            crossover = prev_ema_9 <= prev_ema_21 and current_ema_9 > current_ema_21
            
            logger.debug(f"Easy EMA crossover: {crossover} (9: {current_ema_9:.4f}, 21: {current_ema_21:.4f})")
            return crossover
            
        except Exception as e:
            logger.error(f"Error checking easy EMA crossover: {e}")
            return False
    
    def _check_price_above_ema9(self, df: pd.DataFrame) -> bool:
        """Check if price is above EMA9"""
        try:
            if len(df) < self.settings.ema_9_period:
                return False
            
            ema_9 = self.ta.calculate_ema(df['close'], self.settings.ema_9_period)
            current_price = df['close'].iloc[-1]
            current_ema_9 = ema_9.iloc[-1]
            
            result = current_price > current_ema_9
            logger.debug(f"Price above EMA9: {result} (price: {current_price:.4f}, ema9: {current_ema_9:.4f})")
            return result
            
        except Exception as e:
            logger.error(f"Error checking price above EMA9: {e}")
            return False
    
    def _check_volume_increase(self, df: pd.DataFrame) -> bool:
        """Check for volume increase (simplified)"""
        try:
            if len(df) < 20:
                return False
            
            volume_sma = self.ta.calculate_volume_sma(df['volume'])
            current_volume = df['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            result = current_volume > avg_volume * 1.1  # 10% increase
            logger.debug(f"Volume increase: {result} (current: {current_volume:.0f}, avg: {avg_volume:.0f})")
            return result
            
        except Exception as e:
            logger.error(f"Error checking volume increase: {e}")
            return False
    
    def _check_any_bullish_candle(self, df: pd.DataFrame) -> bool:
        """Check for any bullish candle"""
        try:
            if len(df) < 1:
                return False
            
            current = df.iloc[-1]
            result = current['close'] > current['open']
            
            logger.debug(f"Bullish candle: {result} (close: {current['close']:.4f}, open: {current['open']:.4f})")
            return result
            
        except Exception as e:
            logger.error(f"Error checking bullish candle: {e}")
            return False
    
    def _generate_easy_signal_reason(self, triggers: List[str]) -> str:
        """Generate reason for easy signal"""
        try:
            trigger_descriptions = {
                "easy_ema_crossover": "EMA9/EMA21 crossover",
                "price_above_ema9": "Price above EMA9",
                "volume_increase": "Volume increase",
                "bullish_candle": "Bullish candle"
            }
            
            trigger_texts = [trigger_descriptions.get(t, t) for t in triggers]
            
            if len(trigger_texts) == 1:
                reason = f"Easy signal: {trigger_texts[0]}"
            else:
                reason = f"Easy signal: {', '.join(trigger_texts[:-1])} and {trigger_texts[-1]}"
            
            return reason
            
        except Exception as e:
            logger.error(f"Error generating easy signal reason: {e}")
            return "Easy signal detected"
    
    def should_generate_signal(self, symbol: str, current_signals: List[Dict]) -> bool:
        """Check if we should generate a new signal for this symbol"""
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
            logger.error(f"Error checking easy signal generation: {e}")
            return False
