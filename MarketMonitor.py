#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from OrderBook import OrderBook
import tabulate
import asyncio
from typing import Callable
from collections import Counter
import logging
from KalshiAPI import kalshi_api

_active_monitors = Counter()

async def monitor_event(event: str, handler: Callable, logger: logging.Logger, conditional: Callable = lambda x: True):
    """
    Monitor all markets in an event.

    Args:
        event: Event to monitor
        handler: Function to call with each update
        logger: Logger instance
        conditional: Function that determines if the monitor should continue
    """
    if not conditional(event):
        return
        
    market_list = [m.ticker for m in kalshi_api.get_markets(event_ticker=event).markets]
    logger.info(f"\nEvent {event} markets: {market_list}")
    
    tasks = [
        asyncio.create_task(monitor_market(market_ticker, handler, logger))
        for market_ticker in market_list
    ]
    
    logger.info(f"Created {len(tasks)} monitor_market tasks for event: {event}")
    await asyncio.gather(*tasks, return_exceptions=True) 

async def monitor_market(ticker: str, handler: Callable, logger: logging.Logger, conditional: Callable = lambda: True):
    """
    Monitor a single market's orderbook updates.

    Args:
        ticker: Market ticker to monitor
        function(orderbook, updates, timestamp): Function to call with each update
        logger: Logger instance
        conditional: Function that determines if the monitor should continue
    """
    consumer = None
    try:
        updates = 0
        
        # Track active monitor
        _active_monitors[ticker] += 1
        logger.info(f"Active monitors: {dict(_active_monitors)}")

        async for orderbook in OrderBook.from_kafka(ticker, logger=logger):
            if not conditional():
                logger.info(f"Condition not met for {ticker}")
                break
            try:
                updates += 1
                logger.debug(f"Processing update {updates} for {ticker}")
                handler(orderbook, updates, time.time())
            except asyncio.CancelledError:
                logger.info(f"Shutting down monitor for {ticker}")
                break
            except Exception as e:
                logger.error(f"Error in {ticker}: {e}")
    finally:
        _active_monitors[ticker] -= 1
        if _active_monitors[ticker] == 0:
            del _active_monitors[ticker]

def print_orderbook(orderbook: OrderBook, updates: int, timestamp: float, logger: logging.Logger):
    ticker = orderbook.ticker
    # Print current state
    print("\033[2J\033[H")  # Clear screen and move cursor to top
    print(f"Market: {ticker} (Updates: {updates})")
    
    # Get consolidated book
    book = orderbook.get_book()
    yes_orders = [[size, f"${price/100:.2f}"] for price, size in sorted(book['bids'].items(), reverse=True)]
    no_orders = [[f"${price/100:.2f}", size] for price, size in sorted(book['offers'].items())]
    
    # Ensure both lists have same length for clean display
    max_rows = max(len(yes_orders), len(no_orders))
    yes_orders.extend([["-", "-"]] * (max_rows - len(yes_orders)))
    no_orders.extend([["-", "-"]] * (max_rows - len(no_orders)))
    
    # Combine into single table
    combined_orders = [[*yes_row, *no_row] for yes_row, no_row in zip(yes_orders, no_orders)]
    headers = ['Yes Size', 'Yes Price', 'No Price', 'No Size']
    print(tabulate.tabulate(combined_orders, headers=headers, tablefmt='simple'))
    
    print(f"\nBest Yes: ${orderbook.best_yes.price/100:.2f} ({orderbook.best_yes.quantity})")
    print(f"Best No: ${orderbook.best_no.price/100:.2f} ({orderbook.best_no.quantity})")

    print(f"{orderbook.yes_levels}")
    print(f"{orderbook.no_levels}")

async def main(logger, args):
    """
    Main function to run the market monitor.
    
    Args:
        logger: Logger instance
        args: Parsed arguments
    """
    # If no ticker provided, show available markets
    if not args.ticker:
        from Series import market_list
        print("Available markets:")
        for m in market_list:
            print(f"  {m}")
        print("\nUse --ticker to specify which market to monitor")
        return
    
    await monitor_market(args.ticker, print_orderbook, logger)

if __name__ == "__main__":
    asyncio.run(main())
