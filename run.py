#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging.config
import argparse
from logging_config import LOGGING_CONFIG

from KalshiAPI import kalshi_api

# Import main functions from different modules
from MarketDataService import main as data_service_main
from MarketMonitor import main as monitor_main
from TestStrategy import main as strategy_main

async def run_market_data_system(market_list, args):
    """Run the main trading system"""
    logger = logging.getLogger('MarketData')
    try:
        await data_service_main(market_list, logger, args)
    except Exception as e:
        logger.error(f"Trading system error: {e}", exc_info=True)

async def run_monitor(args):
    """Run the market monitor"""
    logger = logging.getLogger('Monitor')
    try:
        await monitor_main(logger, args)
    except Exception as e:
        logger.error(f"Monitor error: {e}", exc_info=True)

async def run_strategies(args):
    """Run the trading strategies"""
    logger = logging.getLogger('Strategies')
    try:
        await strategy_main(logger, args)
    except Exception as e:
        logger.error(f"Strategy error: {e}", exc_info=True)


async def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run trading system components')
    parser.add_argument('--print', action='store_true', help='Print logs to stdout')
    parser.add_argument('--components', nargs='+', 
                      choices=['monitor', 'strategy'],
                      help='Components to run')
    parser.add_argument('--ticker', type=str,
                      help='Event Ticker to monitor')
    
    args = parser.parse_args()

    # Configure logging
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting trading system...")
    
    tasks = []
    
    if args.ticker:
        market_list = [m.ticker for m in kalshi_api.get_markets(event_ticker=args.ticker).markets]
    else:
        from Series import market_list
    
    # Always run the market data service
    tasks.append(run_market_data_system(market_list, args))

    # Create tasks based on selected components
    if 'monitor' in args.components:
        tasks.append(run_monitor(args))
    if 'strategy' in args.components:
        tasks.append(run_strategies(args))
    
    if tasks:
        try:
            print("Running tasks")
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 
