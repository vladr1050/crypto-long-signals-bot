"""
Aggressive signal detector for bounce/reversal strategies
Uses RSI oversold bounce + EMA crossover + Volume surge
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

from app.config.settings import Settings
from app.core.indicators.ta import TechnicalAnalysis
from app.core.risk.sizing import RiskManager

logger = logging.getLogger(__name__)


class AggressiveSignalDetector:
    """Aggressive signal detector for oversold bounce strategies"""
    
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.ta = TechnicalAnalysis()
        self.risk_manager = RiskManager()
    
    def detect_signals(
        self, 
        market_data: Dict[str, Dict[str, pd.DataFrame]], 
        user_risk_pct: float = None
    ) -> List[Dict]:
        """
        Detect aggressive signals for all symbols
        
        Args:
            market_data: Dict of {symbol: {timeframe: DataFrame}}
            user_risk_pct: User's risk percentage (overrides default)
            
        Returns:
            List of signal dictionaries
        """
        try:
            signals = []
            
            for symbol, timeframes in market_data.items():
                signal = self._detect_signal_for_symbol(symbol, timeframes, user_risk_pct)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error detecting aggressive signals: {e}")
            return []
    
    def _detect_signal_for_symbol(
        self, 
        symbol: str, 
        timeframes: Dict[str, pd.DataFrame],
        user_risk_pct: float = None
    ) -> Optional[Dict]:
        """
        Detect aggressive signal for a specific symbol
        
        Args:
            symbol: Trading pair symbol
            timeframes: Dict of {timeframe: DataFrame}
            user_risk_pct: User's risk percentage (overrides default)
            
        Returns:
            Signal dict or None if no signal
        """
        try:
            # Get required timeframes
            entry_df = timeframes.get(self.settings.entry_timeframe)  # 15m
            trend_df = timeframes.get(self.settings.trend_timeframe)  # 1h
            confirmation_df = timeframes.get(self.settings.confirmation_timeframe)  # 5m
            
            if not all([entry_df is not None, trend_df is not None, confirmation_df is not None]):
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Check minimum data requirements
            if len(entry_df) < 50 or len(trend_df) < 200 or len(confirmation_df) < 30:
                logger.warning(f"Insufficient data length for {symbol}")
                return None
            
            # Apply aggressive filter (RSI bounce from oversold)
            if not self._check_aggressive_filter(entry_df):
                return None
            
            # Check entry triggers (need ≥3 out of 4: RSI bounce + EMA crossover + Volume + Trend strengthening)
            triggers = self._check_aggressive_entry_triggers(entry_df, confirmation_df)
            if len(triggers) < 3:  # Need at least 3 out of 4 conditions
                return None
            
            # Calculate signal parameters
            entry_price = entry_df['close'].iloc[-1]
            stop_loss = self.ta.calculate_stop_loss(entry_df, entry_price, is_easy_mode=True)
            
            # Calculate technical take profits (same dynamic logic as other detectors)
            tp1, tp2 = self.ta.calculate_technical_take_profits(entry_df, entry_price)
            
            # Validate risk parameters
            risk_pct = user_risk_pct if user_risk_pct is not None else self.settings.default_risk_pct
            is_valid, error_msg = self.risk_manager.validate_risk_parameters(
                risk_pct, entry_price, stop_loss, is_easy_mode=True
            )
            
            if not is_valid:
                logger.warning(f"Invalid risk parameters for {symbol}: {error_msg}")
                return None
            
            # Use technical take profits (dynamic as requested)
            tp1, tp2 = self.risk_manager.calculate_take_profits(entry_price, stop_loss, tp1, tp2)
            
            # Calculate signal grade
            grade = "C"  # Aggressive signals are always C grade (high risk)
            
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
                'reason': self._generate_aggressive_signal_reason(triggers),
                'triggers': triggers,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=18)  # 18h for aggressive
            }
            
            logger.info(f"Aggressive signal detected for {symbol}: {grade} grade, {risk_reward:.2f} R/R")
            return signal
            
        except Exception as e:
            logger.error(f"Error detecting aggressive signal for {symbol}: {e}")
            return None
    
    def _check_aggressive_filter(self, entry_df: pd.DataFrame) -> bool:
        """
        Check aggressive filter (RSI bounce from oversold)
        
        Args:
            entry_df: 15m timeframe data
            
        Returns:
            True if RSI bounce detected
        """
        try:
            # RSI was below 30 and now crossed above
            rsi = self.ta.calculate_rsi(entry_df['close'], 14)
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else 0
            
            # RSI was oversold (< 30) and now crossed above 30
            rsi_bounce = prev_rsi < 30 and current_rsi >= 30
            
            logger.debug(f"Aggressive filter (RSI bounce): {rsi_bounce} (current: {current_rsi:.1f}, prev: {prev_rsi:.1f})")
            return rsi_bounce
            
        except Exception as e:
            logger.error(f"Error checking aggressive filter: {e}")
            return False
    
    def _check_aggressive_entry_triggers(
        self, 
        entry_df: pd.DataFrame, 
        confirmation_df: pd.DataFrame
    ) -> List[str]:
        """
        Check aggressive entry trigger conditions (need ≥3 out of 4)
        1. RSI bounce (< 30 then >= 30)
        2. EMA crossover (price crosses EMA50 from below)
        3. Volume surge (last candle volume >= 1.5x average)
        4. Trend strengthening (EMA20 > EMA50)
        
        Args:
            entry_df: 15m timeframe data
            confirmation_df: 5m timeframe data
            
        Returns:
            List of triggered conditions
        """
        triggers = []
        
        try:
            # 1. RSI bounce condition (already checked in filter, but verify)
            rsi = self.ta.calculate_rsi(entry_df['close'], 14)
            current_rsi = rsi.iloc[-1]
            if current_rsi >= 30 and current_rsi < 50:  # Recovered from oversold, not overbought
                triggers.append("rsi_bounce")
            
            # 2. EMA crossover (price crosses EMA50 from below)
            ema_50 = self.ta.calculate_ema(entry_df['close'], 50)
            current_price = entry_df['close'].iloc[-1]
            prev_price = entry_df['close'].iloc[-2]
            current_ema_50 = ema_50.iloc[-1]
            prev_ema_50 = ema_50.iloc[-2]
            
            # Price was below EMA50 and now above OR price just crossed EMA50
            price_cross = (prev_price <= prev_ema_50 and current_price > current_ema_50) or \
                         (prev_price < prev_ema_50 and current_price >= current_ema_50)
            
            if price_cross:
                triggers.append("ema_crossover")
            
            # 3. Volume surge (last candle >= 1.5x average over 20 candles)
            volume = entry_df['volume']
            if len(volume) >= 20:
                current_volume = volume.iloc[-1]
                avg_volume = volume.tail(20).mean()
                volume_surge = current_volume >= avg_volume * 1.5
                
                if volume_surge:
                    triggers.append("volume_surge")
            
            # 4. EMA20 > EMA50 (trend strengthening)
            ema_20 = self.ta.calculate_ema(entry_df['close'], 20)
            current_ema_20 = ema_20.iloc[-1]
            
            if current_ema_20 > current_ema_50:
                triggers.append("trend_strengthening")
            
            logger.debug(f"Aggressive triggers: {triggers}")
            
        except Exception as e:
            logger.error(f"Error checking aggressive entry triggers: {e}")
        
        return triggers
    
    def _generate_aggressive_signal_reason(self, triggers: List[str]) -> str:
        """Generate reason for aggressive signal"""
        try:
            trigger_descriptions = {
                "rsi_bounce": "RSI bounce from oversold",
                "ema_crossover": "EMA crossover",
                "volume_surge": "Volume surge",
                "trend_strengthening": "Trend strengthening"
            }
            
            trigger_texts = [trigger_descriptions.get(t, t) for t in triggers]
            
            if len(trigger_texts) == 3:
                reason = f"Aggressive signal: {', '.join(trigger_texts)}"
            else:
                reason = f"Aggressive signal: {', '.join(trigger_texts)}"
            
            return reason
            
        except Exception as e:
            logger.error(f"Error generating aggressive signal reason: {e}")
            return "Aggressive signal detected"
    
    def should_generate_signal(self, symbol: str, current_signals: List[Dict]) -> bool:
        """Check if we should generate a new signal for this symbol"""
        try:
            # Check max concurrent signals
            if len(current_signals) >= self.settings.max_concurrent_signals:
                logger.debug(f"Max concurrent signals reached for {symbol}")
                return False
            
            # Check if we already have a signal for this symbol
            active_for_symbol = [s for s in current_signals if s.get('symbol') == symbol and s.get('status') == 'active']
            if active_for_symbol:
                logger.debug(f"Active signal already exists for {symbol}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if should generate signal: {e}")
            return True
