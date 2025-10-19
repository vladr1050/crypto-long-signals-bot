"""
Technical analysis indicators for signal detection
"""
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import ta

logger = logging.getLogger(__name__)


class TechnicalAnalysis:
    """Technical analysis calculations for signal detection"""
    
    def __init__(self):
        self.rsi_period = 14
        self.ema_200_period = 200
        self.ema_50_period = 50
        self.ema_9_period = 9
        self.ema_21_period = 21
        self.bb_period = 20
        self.bb_std = 2.0
        self.atr_period = 14
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return ta.trend.EMAIndicator(data, window=period).ema_indicator()
    
    def calculate_rsi(self, data: pd.Series, period: int = None) -> pd.Series:
        """Calculate RSI"""
        if period is None:
            period = self.rsi_period
        return ta.momentum.RSIIndicator(data, window=period).rsi()
    
    def calculate_bollinger_bands(self, data: pd.Series, period: int = None, std: float = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        if period is None:
            period = self.bb_period
        if std is None:
            std = self.bb_std
        
        bb = ta.volatility.BollingerBands(data, window=period, window_dev=std)
        return bb.bollinger_hband(), bb.bollinger_lband(), bb.bollinger_mavg()
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = None) -> pd.Series:
        """Calculate Average True Range"""
        if period is None:
            period = self.atr_period
        return ta.volatility.AverageTrueRange(high, low, close, window=period).average_true_range()
    
    def calculate_volume_sma(self, volume: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Simple Moving Average of volume"""
        return volume.rolling(window=period).mean()
    
    def is_trend_bullish(self, df: pd.DataFrame) -> bool:
        """
        Check if trend is bullish based on EMA200 (1h) and EMA50 (15m)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if trend is bullish
        """
        try:
            if len(df) < max(self.ema_200_period, self.ema_50_period):
                return False
            
            # Calculate EMAs
            ema_200 = self.calculate_ema(df['close'], self.ema_200_period)
            ema_50 = self.calculate_ema(df['close'], self.ema_50_period)
            
            # Check if price is above both EMAs
            current_price = df['close'].iloc[-1]
            current_ema_200 = ema_200.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            
            return current_price > current_ema_200 and current_price > current_ema_50
            
        except Exception as e:
            logger.error(f"Error checking trend: {e}")
            return False
    
    def is_rsi_neutral_bullish(self, df: pd.DataFrame) -> bool:
        """
        Check if RSI is in neutral to slightly bullish range (45-65)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if RSI is in range
        """
        try:
            if len(df) < self.rsi_period:
                return False
            
            rsi = self.calculate_rsi(df['close'])
            current_rsi = rsi.iloc[-1]
            
            return 45 <= current_rsi <= 65
            
        except Exception as e:
            logger.error(f"Error checking RSI: {e}")
            return False
    
    def check_breakout_retest(self, df: pd.DataFrame) -> bool:
        """
        Check for breakout and retest of local resistance
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if breakout and retest pattern detected
        """
        try:
            if len(df) < 50:  # Need enough data for pattern
                return False
            
            # Find recent high (resistance level)
            recent_data = df.tail(20)
            resistance = recent_data['high'].max()
            
            # Check if price broke above resistance
            current_price = df['close'].iloc[-1]
            if current_price <= resistance:
                return False
            
            # Check if there was a retest (price came back to resistance area)
            retest_threshold = resistance * 0.995  # 0.5% below resistance
            retest_data = recent_data.tail(10)
            retest_occurred = (retest_data['low'] <= retest_threshold).any()
            
            return retest_occurred
            
        except Exception as e:
            logger.error(f"Error checking breakout retest: {e}")
            return False
    
    def check_bollinger_squeeze_expansion(self, df: pd.DataFrame) -> bool:
        """
        Check for Bollinger Bands squeeze expansion with increased volume
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if squeeze expansion with volume detected
        """
        try:
            if len(df) < self.bb_period + 10:
                return False
            
            # Calculate Bollinger Bands
            bb_upper, bb_lower, bb_middle = self.calculate_bollinger_bands(df['close'])
            
            # Check for squeeze (bands close together)
            band_width = (bb_upper - bb_lower) / bb_middle
            current_width = band_width.iloc[-1]
            avg_width = band_width.tail(10).mean()
            
            # Check for expansion (current width > average)
            width_expansion = current_width > avg_width * 1.1
            
            # Check for volume increase
            volume_sma = self.calculate_volume_sma(df['volume'])
            current_volume = df['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            volume_increase = current_volume > avg_volume * 1.2
            
            return width_expansion and volume_increase
            
        except Exception as e:
            logger.error(f"Error checking Bollinger squeeze: {e}")
            return False
    
    def check_ema_crossover(self, df: pd.DataFrame) -> bool:
        """
        Check for EMA9/EMA21 bullish crossover above EMA50
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if bullish crossover detected
        """
        try:
            if len(df) < max(self.ema_9_period, self.ema_21_period, self.ema_50_period):
                return False
            
            # Calculate EMAs
            ema_9 = self.calculate_ema(df['close'], self.ema_9_period)
            ema_21 = self.calculate_ema(df['close'], self.ema_21_period)
            ema_50 = self.calculate_ema(df['close'], self.ema_50_period)
            
            # Check current values
            current_ema_9 = ema_9.iloc[-1]
            current_ema_21 = ema_21.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            
            # Check previous values for crossover
            prev_ema_9 = ema_9.iloc[-2]
            prev_ema_21 = ema_21.iloc[-2]
            
            # Crossover: EMA9 crosses above EMA21
            crossover = prev_ema_9 <= prev_ema_21 and current_ema_9 > current_ema_21
            
            # Both above EMA50
            above_ema_50 = current_ema_9 > current_ema_50 and current_ema_21 > current_ema_50
            
            return crossover and above_ema_50
            
        except Exception as e:
            logger.error(f"Error checking EMA crossover: {e}")
            return False
    
    def check_bullish_candle(self, df: pd.DataFrame) -> bool:
        """
        Check for bullish engulfing or long-wick candle with higher volume
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if bullish candle pattern detected
        """
        try:
            if len(df) < 3:
                return False
            
            # Get last 3 candles
            current = df.iloc[-1]
            previous = df.iloc[-2]
            prev_prev = df.iloc[-3]
            
            # Check for bullish engulfing
            bullish_engulfing = (
                previous['close'] < previous['open'] and  # Previous bearish
                current['close'] > current['open'] and    # Current bullish
                current['open'] < previous['close'] and   # Current opens below prev close
                current['close'] > previous['open']       # Current closes above prev open
            )
            
            # Check for long lower wick (hammer-like)
            body_size = abs(current['close'] - current['open'])
            lower_wick = current['open'] - current['low'] if current['close'] > current['open'] else current['close'] - current['low']
            upper_wick = current['high'] - current['close'] if current['close'] > current['open'] else current['high'] - current['open']
            
            long_lower_wick = lower_wick > body_size * 2 and upper_wick < body_size
            
            # Check for volume increase
            volume_sma = self.calculate_volume_sma(df['volume'])
            current_volume = current['volume']
            avg_volume = volume_sma.iloc[-1]
            volume_increase = current_volume > avg_volume * 1.1
            
            return (bullish_engulfing or long_lower_wick) and volume_increase
            
        except Exception as e:
            logger.error(f"Error checking bullish candle: {e}")
            return False
    
    def calculate_support_resistance(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[float, float]:
        """
        Calculate support and resistance levels
        
        Args:
            df: DataFrame with OHLCV data
            lookback: Number of periods to look back
            
        Returns:
            Tuple of (support, resistance)
        """
        try:
            recent_data = df.tail(lookback)
            support = recent_data['low'].min()
            resistance = recent_data['high'].max()
            return support, resistance
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return 0.0, 0.0
    
    def calculate_stop_loss(self, df: pd.DataFrame, entry_price: float) -> float:
        """
        Calculate stop loss level
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price for the position
            
        Returns:
            Stop loss price
        """
        try:
            # Method 1: Below local swing low
            support, _ = self.calculate_support_resistance(df)
            sl_swing = support * 0.995  # 0.5% below support
            
            # Method 2: 1.5x ATR from entry
            atr = self.calculate_atr(df['high'], df['low'], df['close'])
            current_atr = atr.iloc[-1]
            sl_atr = entry_price - (1.5 * current_atr)
            
            # Take the larger (more conservative) stop loss
            return max(sl_swing, sl_atr)
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return entry_price * 0.98  # Fallback: 2% below entry