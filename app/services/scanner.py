"""
Market scanner service for detecting trading signals
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import get_settings
from app.core.data.market import MarketDataService
from app.core.signals.detector import SignalDetector
from app.core.signals.easy_detector import EasySignalDetector
from app.services.notifier import NotificationService

logger = logging.getLogger(__name__)


class MarketScanner:
    """Market scanner for detecting trading signals"""
    
    def __init__(
        self, 
        db_repo, 
        market_data: MarketDataService, 
        signal_detector: SignalDetector,
        notifier: NotificationService,
        settings
    ):
        self.db_repo = db_repo
        self.market_data = market_data
        self.signal_detector = signal_detector
        self.notifier = notifier
        self.settings = settings
        
        # Add easy detector for testing
        from app.core.indicators.ta import TechnicalAnalysis
        from app.core.risk.sizing import RiskManager
        ta = TechnicalAnalysis()
        risk_manager = RiskManager()
        self.easy_detector = EasySignalDetector(ta, risk_manager)
        
        # Initialize scheduler
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        # Statistics
        self.scan_count = 0
        self.signals_generated = 0
        self.last_scan_time = None
    
    async def start(self):
        """Start the market scanner"""
        try:
            if self.is_running:
                logger.warning("Scanner is already running")
                return
            
            # Schedule scanning job
            self.scheduler.add_job(
                self._scan_markets,
                trigger=IntervalTrigger(seconds=self.settings.scan_interval_sec),
                id="market_scanner",
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            # Run initial scan
            await self._scan_markets()
            
            logger.info("🚀 Market scanner started successfully")
            
        except Exception as e:
            logger.error(f"Error starting market scanner: {e}")
            raise
    
    async def stop(self):
        """Stop the market scanner"""
        try:
            if not self.is_running:
                return
            
            self.scheduler.shutdown()
            self.is_running = False
            
            logger.info("🛑 Market scanner stopped")
            
        except Exception as e:
            logger.error(f"Error stopping market scanner: {e}")
    
    async def _scan_markets(self):
        """Scan markets for trading signals"""
        try:
            self.scan_count += 1
            self.last_scan_time = datetime.utcnow()
            
            logger.info(f"🔍 Starting market scan #{self.scan_count}")
            
            # Get enabled pairs
            pairs = await self.db_repo.get_enabled_pairs()
            if not pairs:
                logger.warning("No enabled pairs found")
                return
            
            # Get active signals to avoid duplicates
            active_signals = await self.db_repo.get_active_signals()
            active_symbols = {signal.symbol for signal in active_signals}
            
            # Prepare symbols list
            symbols = [pair.symbol for pair in pairs if pair.symbol not in active_symbols]
            
            # Debug: log symbols
            logger.info(f"Symbols from database: {symbols}")
            for i, symbol in enumerate(symbols):
                logger.info(f"Symbol {i}: '{symbol}' (type: {type(symbol)}, repr: {repr(symbol)})")
            
            if not symbols:
                logger.info("All pairs have active signals, skipping scan")
                return
            
            # Required timeframes
            timeframes = [
                self.settings.trend_timeframe,
                self.settings.entry_timeframe,
                self.settings.confirmation_timeframe
            ]
            
            # Fetch market data for all symbols and timeframes
            logger.info(f"Fetching data for {len(symbols)} symbols")
            market_data = await self.market_data.get_multiple_ohlcv(symbols, timeframes)
            
            # Detect signals using appropriate detector
            if self.settings.use_easy_detector:
                signals = self.easy_detector.detect_signals(market_data)
                logger.info("Using EasySignalDetector for signal detection")
            else:
                signals = self.signal_detector.detect_signals(market_data)
                logger.info("Using SignalDetector for signal detection")
            
            if signals:
                logger.info(f"🎯 Detected {len(signals)} signals")
                await self._process_signals(signals)
            else:
                logger.info("No signals detected in this scan")
                # Add detailed logging for debugging
                for symbol, tf_data in market_data.items():
                    logger.debug(f"Checking {symbol}:")
                    trend_df = tf_data.get(self.settings.trend_timeframe)
                    entry_df = tf_data.get(self.settings.entry_timeframe)
                    confirmation_df = tf_data.get(self.settings.confirmation_timeframe)
                    
                    if not all([df is not None and not df.empty for df in [trend_df, entry_df, confirmation_df]]):
                        logger.debug(f"  {symbol}: Insufficient data")
                        continue
                    
                    # Check trend filter
                    trend_bullish = self.signal_detector.ta.is_trend_bullish(trend_df)
                    entry_trend_bullish = self.signal_detector.ta.is_trend_bullish(entry_df)
                    rsi_neutral = self.signal_detector.ta.is_rsi_neutral_bullish(trend_df)
                    
                    logger.debug(f"  {symbol}: Trend filter - 1h: {trend_bullish}, 15m: {entry_trend_bullish}, RSI: {rsi_neutral}")
                    
                    if not (trend_bullish and entry_trend_bullish and rsi_neutral):
                        logger.debug(f"  {symbol}: Trend filter failed")
                        continue
                    
                    # Check triggers
                    triggers = []
                    if self.signal_detector.ta.check_breakout_retest(entry_df):
                        triggers.append("breakout_retest")
                    if self.signal_detector.ta.check_bollinger_squeeze_expansion(entry_df):
                        triggers.append("bb_squeeze_expansion")
                    if self.signal_detector.ta.check_ema_crossover(entry_df):
                        triggers.append("ema_crossover")
                    if self.signal_detector.ta.check_bullish_candle(confirmation_df):
                        triggers.append("bullish_candle")
                    
                    logger.debug(f"  {symbol}: Triggers - {len(triggers)}/4: {triggers}")
                    
                    if len(triggers) < 2:
                        logger.debug(f"  {symbol}: Not enough triggers (need ≥2)")
                        continue
                    
                    logger.debug(f"  {symbol}: Would generate signal!")
            
            # Clean up expired signals
            await self._cleanup_expired_signals()
            
            logger.info(f"✅ Scan #{self.scan_count} completed")
            
        except Exception as e:
            logger.error(f"Error in market scan: {e}")
    
    async def _process_signals(self, signals: List[Dict]):
        """Process detected signals"""
        try:
            for signal_data in signals:
                # Check if we should generate this signal
                current_signals = await self.db_repo.get_active_signals()
                if not self.signal_detector.should_generate_signal(signal_data['symbol'], current_signals):
                    continue
                
                # Create signal in database
                signal = await self.db_repo.create_signal(
                    symbol=signal_data['symbol'],
                    timeframe=signal_data['timeframe'],
                    entry_price=signal_data['entry_price'],
                    stop_loss=signal_data['stop_loss'],
                    take_profit_1=signal_data['take_profit_1'],
                    take_profit_2=signal_data['take_profit_2'],
                    grade=signal_data['grade'],
                    risk_level=signal_data['risk_level'],
                    reason=signal_data['reason'],
                    expires_at=signal_data['expires_at']
                )
                
                # Add signal ID to data for notifications
                signal_data['id'] = signal.id
                
                # Log signal
                logger.info(
                    f"Signal created: {signal.symbol} {signal.grade} "
                    f"Entry: {signal.entry_price} SL: {signal.stop_loss} "
                    f"TP1: {signal.take_profit_1} TP2: {signal.take_profit_2}"
                )
                
                # Send notification to all users
                await self._send_signal_to_users(signal_data)
                
                self.signals_generated += 1
            
        except Exception as e:
            logger.error(f"Error processing signals: {e}")
    
    async def _send_signal_to_users(self, signal_data: Dict):
        """Send signal notification to all users who want signals"""
        try:
            # Get all users who want signals
            users = await self.db_repo.get_users_with_signals_enabled()
            
            if not users:
                logger.info("No users with signals enabled")
                return
            
            # Get bot instance from main app
            # For now, we'll need to pass bot instance to scanner
            # This is a temporary solution - in production, use dependency injection
            from app.main import get_bot_instance
            bot = get_bot_instance()
            
            if not bot:
                logger.error("Bot instance not available for sending signals")
                return
            
            # Send to each user
            sent_count = 0
            for user in users:
                try:
                    success = await self.notifier.send_signal(
                        bot=bot,
                        user_id=user.telegram_id,
                        signal=signal_data,
                        db_repo=self.db_repo
                    )
                    if success:
                        sent_count += 1
                        logger.info(f"Signal sent to user {user.telegram_id}")
                    else:
                        logger.warning(f"Failed to send signal to user {user.telegram_id}")
                except Exception as e:
                    logger.error(f"Error sending signal to user {user.telegram_id}: {e}")
            
            logger.info(f"Signal sent to {sent_count}/{len(users)} users")
            
        except Exception as e:
            logger.error(f"Error sending signal to users: {e}")
    
    async def _cleanup_expired_signals(self):
        """Clean up expired signals"""
        try:
            expired_count = await self.db_repo.expire_old_signals()
            if expired_count > 0:
                logger.info(f"Expired {expired_count} old signals")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired signals: {e}")
    
    async def get_scanner_status(self) -> Dict:
        """Get scanner status information"""
        try:
            return {
                'is_running': self.is_running,
                'scan_count': self.scan_count,
                'signals_generated': self.signals_generated,
                'last_scan_time': self.last_scan_time,
                'scan_interval_sec': self.settings.scan_interval_sec,
                'enabled_pairs': len(await self.db_repo.get_enabled_pairs()),
                'active_signals': len(await self.db_repo.get_active_signals())
            }
            
        except Exception as e:
            logger.error(f"Error getting scanner status: {e}")
            return {
                'is_running': False,
                'error': str(e)
            }
    
    async def force_scan(self) -> Dict:
        """Force an immediate market scan"""
        try:
            logger.info("🔄 Forcing immediate market scan")
            await self._scan_markets()
            
            return {
                'success': True,
                'message': f"Scan completed. Generated {self.signals_generated} signals total."
            }
            
        except Exception as e:
            logger.error(f"Error in force scan: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_scan_statistics(self) -> Dict:
        """Get detailed scan statistics"""
        try:
            active_signals = await self.db_repo.get_active_signals()
            enabled_pairs = await self.db_repo.get_enabled_pairs()
            
            # Calculate signal distribution by grade
            grade_distribution = {}
            for signal in active_signals:
                grade = signal.grade
                grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
            
            return {
                'total_scans': self.scan_count,
                'total_signals_generated': self.signals_generated,
                'active_signals': len(active_signals),
                'enabled_pairs': len(enabled_pairs),
                'grade_distribution': grade_distribution,
                'last_scan': self.last_scan_time.isoformat() if self.last_scan_time else None,
                'scanner_running': self.is_running
            }
            
        except Exception as e:
            logger.error(f"Error getting scan statistics: {e}")
            return {'error': str(e)}