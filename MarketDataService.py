#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
# Main async event loop.
# Should pull in the list of markets from Series.py
# Then, subscribe to orderbook deltas for all markets
# Every update should be processed and update an Orderbook object for the corresponding market
# If the update is a snapshot, set the orderbook object to the new snapshot
# If the update is a delta, update the orderbook object with the delta
# This should be able to keep track of sequence numbers and raise an error if there is a missing seqno.

import asyncio
import signal
import logging
from datetime import datetime
from KalshiWebsocketClient import KalshiWebsocketClient
from OrderBook import OrderBook
from typing import Dict, Any, Optional
import json
import argparse
import sys
import os

# Add logging setup at the top
def setup_logging(print_to_stdout=False):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'logs/trading_system_{timestamp}.log'
    print(log_filename)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # File handler (always enabled)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Stream handler (optional)
    if print_to_stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(stream_handler)
    
    return logger

class OrderbookManager:
    def __init__(self, logger: logging.Logger):
        """Initialize OrderbookManager with a logger.
        
        Args:
            logger: Logger instance for logging messages
        """
        self.orderbooks: Dict[str, OrderBook] = {}
        # Track sequence numbers per channel instead of per market
        self.sequence_numbers: Dict[str, int] = {
            'orderbook_delta': -1,
            'orderbook_snapshot': -1,
            'trade': -1
        }
        self.logger = logger
    
    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process messages from websocket"""
        self.logger.info("\n\nProcessing update...")
        
        channel = message.get('type')
        if not channel:
            self.logger.error(f"No message type / channel specified in {message}")
            raise ValueError(f"No message type / channel specified in {message}")
            return
            
        seq_no = message.get('seq')
        self.logger.info(f"\"{channel}\" seqno: {seq_no}")

        # Get message content from the 'msg' field
        msg_content = message.get('msg', {})
        market_ticker = msg_content.get('market_ticker', None)

        if market_ticker is None and channel != 'subscribed':
            self.logger.info(f"No market ticker in {channel} message")
            return

        try:
            # Process snapshot or delta
            match channel:
                case 'subscribed':
                    self._process_subscription(msg_content)
                case 'ticker':
                    self.logger.info('Ticker update ignored')
                case 'trade':
                    self._process_trade(msg_content)
                    self._check_sequence(channel, seq_no)
                case 'orderbook_snapshot':
                    await self._process_orderbook_snapshot(market_ticker, msg_content)
                    self._check_sequence(channel, seq_no)
                case 'orderbook_delta':
                    await self._process_orderbook_delta(market_ticker, msg_content)
                    self._check_sequence(channel, seq_no)
                case _:
                    self.logger.info(f"Unknown message type: {channel}")
                    self.logger.info(f"Message: {json.dumps(message, indent=2)}")
                    return
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            self.logger.error(f"Message: {json.dumps(message, indent=2)}")
            raise

    def _process_subscription(self, msg_content: Dict) -> None:
        """Process subscription confirmation messages"""
        self.logger.info(f"Subscription confirmed for {msg_content.get('channel')}")

    def _process_trade(self, msg_content: Dict) -> None:
        """Process trade messages"""
        self.logger.info(f"New trade: Market={msg_content.get('market_ticker')}, "
                       f"Price={msg_content.get('price')}, "
                       f"Size={msg_content.get('size')}, "
                       f"Side={msg_content.get('side')}")

    async def _process_orderbook_snapshot(self, market_ticker: str, msg_content: Dict) -> None:
        """Process orderbook snapshot messages"""
        self.logger.info(f"Received snapshot for {market_ticker}")
        # Create OrderBook and initialize its producer
        orderbook = OrderBook(msg_content, logger=self.logger)
        await orderbook.initialize_producer()
        self.orderbooks[market_ticker] = orderbook

    async def _process_orderbook_delta(self, market_ticker: str, msg_content: Dict) -> None:
        """Process orderbook delta messages"""
        self.logger.info(f"Received update for {market_ticker}")
        if market_ticker not in self.orderbooks:
            raise ValueError(f"Received delta before snapshot for {market_ticker}")
        await self.orderbooks[market_ticker].update(msg_content)

    def _check_sequence(self, channel: str, seq_no: Optional[int]) -> None:
        #self.logger.info(f"Checking sequence for {channel} with seqno {seq_no}")
        """Check sequence number for a specific channel"""
        if seq_no is None:
            raise ValueError(f"Missing sequence number in {channel} update")
            
        last_seq = self.sequence_numbers[channel]
        if last_seq != -1 and seq_no != last_seq + 1:
            raise ValueError(f"Missing sequence number for {channel} channel. Expected {last_seq + 1}, got {seq_no}")
            
        self.sequence_numbers[channel] = seq_no

    async def close(self):
        """Clean up all orderbook resources"""
        self.logger.info("Closing all orderbook connections...")
        close_tasks = [
            orderbook.close() 
            for orderbook in self.orderbooks.values()
        ]
        await asyncio.gather(*close_tasks, return_exceptions=True)

async def shutdown(signal, loop, client, manager, logger):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received exit signal {signal.name}...")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    for task in tasks:
        task.cancel()
    
    logger.info("Closing websocket connection...")
    await client.close()
    
    logger.info("Closing orderbook connections...")
    await manager.close()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    print("Shutdown complete.")
    logger.info("Shutdown complete.")

async def main(market_list, logger, args):
    # Get the current event loop
    loop = asyncio.get_running_loop()
    
    # Initialize the orderbook manager with logger
    manager = OrderbookManager(logger)
    
    # Initialize websocket client
    client = KalshiWebsocketClient(
        email=os.getenv('KALSHI_PROD_EMAIL'),
        password=os.getenv('KALSHI_PROD_PASSWORD'),
        env="prod"
    )
    
    # Add signal handlers
    signals = (signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(
                shutdown(s, loop, client, manager, logger)
            )
        )
    
    # Callback to process messages
    async def message_callback(message: Dict[str, Any]):
        try:
            logger.info(f"Received message: {message}")
            await manager.process_message(message)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(f"Message: {json.dumps(message, indent=2)}")
    
    try:
        # Connect to websocket
        await client.connect()
        
        # Subscribe to ticker updates for all markets
        await client.subscribe_ticker(market_list)

        # Subscribe to orderbook updates for all markets
        await client.subscribe_orderbook(market_list)
        
        # Start listening for updates
        logger.info(f"Listening for orderbook and trade updates on {len(market_list)} markets...")
        logger.info("Press Ctrl+C to exit")
        await client.listen(message_callback)
        
    except asyncio.CancelledError:
        logger.info("Main task cancelled")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        # Remove signal handlers
        for sig in signals:
            loop.remove_signal_handler(sig)

if __name__ == "__main__":
    from Series import market_list
    # Get command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--print', action='store_true', help='Print logs to stdout')
    args = parser.parse_args()

    # Setup logging with optional stdout
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # File handler (always enabled)
    file_handler = logging.FileHandler('logs/trading_system.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Stream handler (optional)
    if args.print:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(stream_handler)

    try:
        asyncio.run(main(market_list, logger, args))
    except KeyboardInterrupt:
        print("Received keyboard interrupt...")
        logger.info("Received keyboard interrupt...")
