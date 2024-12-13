#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, List, Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import asyncio
import logging
from dataclasses import dataclass

@dataclass
class PriceLevel:
    price: int
    quantity: int | None

    def __repr__(self):
        return f"{self.quantity}@{self.price}¢"

class OrderBook:
    def __init__(self, orderbook_dict: Dict, kafka_bootstrap_servers: str = 'localhost:9092', 
                 publish_to_kafka: bool = True, logger: Optional[logging.Logger] = None) -> None:
        """Initialize OrderBook instance.
        
        Args:
            orderbook_dict: Dictionary containing orderbook state
            kafka_bootstrap_servers: Kafka bootstrap servers address (default: 'localhost:9092')
            publish_to_kafka: Whether to publish updates to Kafka (default: True)
            logger: Logger instance for logging messages (default: None)
        """
        self.logger = logger

        if not isinstance(orderbook_dict, dict):
            error_msg = "orderbook_dict must be a dictionary"
            self._log_error(error_msg)
            raise TypeError(error_msg)

        ticker = orderbook_dict.get('market_ticker')
        if ticker is None:
            raise ValueError("ticker is required")
        else:
            self.ticker = ticker
        
        # Transform lists into price -> quantity dictionaries
        yes_orders = orderbook_dict.get('yes', [])
        no_orders = orderbook_dict.get('no', [])

        if type(yes_orders) == dict:
            yes_orders = yes_orders.items()
        if type(no_orders) == dict:
            no_orders = no_orders.items()
        
        self.yes_levels = {
            int(price): int(quantity) 
            for price, quantity in yes_orders
            if quantity > 0
        }

        self.no_levels = {
            int(price): int(quantity) 
            for price, quantity in no_orders
            if quantity > 0
        }

        # Initialize best prices for both sides
        self._update_top_of_book()
        
        # Initialize Kafka producer as None - we'll create it asynchronously
        self.producer = None
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.should_publish = publish_to_kafka
        
        if publish_to_kafka:
            # Don't publish in constructor - needs to be done async
            self._pending_messages = []

    async def initialize_producer(self):
        """Initialize the Kafka producer asynchronously"""
        if self.should_publish and self.producer is None:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await self.producer.start()
            
            # Send any pending messages
            for msg in self._pending_messages:
                await self._publish_to_kafka(msg)
            self._pending_messages = []

    async def _publish_to_kafka(self, orderbook_dict: Dict = None) -> None:
        """Publish current orderbook state to Kafka topic."""
        if not self.should_publish:
            return

        if self.producer is None:
            self._pending_messages.append(orderbook_dict or {
                'market_ticker': self.ticker,
                'yes': self.yes_levels,
                'no': self.no_levels
            })
            return

        topic = f"orderbook.{self.ticker}"
        if orderbook_dict is None:
            orderbook_dict = {
                'market_ticker': self.ticker,
                'yes': self.yes_levels,
                'no': self.no_levels
            }

        await self.producer.send_and_wait(topic, orderbook_dict)

    async def update(self, msg: Dict) -> None:
        """Update orderbook with delta and publish to Kafka."""
        side = msg.get('side')
        price = msg.get('price')
        size_delta = msg.get('delta')
        
        if not all([side, price is not None, size_delta is not None]):
            error_msg = "Delta message missing required fields"
            self._log_error(error_msg)
            raise ValueError(error_msg)

        self._log_info(f"Updating {self.ticker}:{side} with price {price} and delta {size_delta}")
        
        # Update correct side of orderbook
        self._update_side(side, price, size_delta)
        
        await self._publish_to_kafka()

    @classmethod
    async def from_kafka(cls, ticker: str, kafka_bootstrap_servers: str = 'localhost:9092', logger: Optional[logging.Logger] = None):
        """Create an async iterator for consuming OrderBook updates from Kafka.
        
        This method encapsulates the consumer lifecycle (start/stop) and ensures proper cleanup.
        It yields OrderBook instances directly, making it easier and safer to use.
        
        Usage:
            async for orderbook in OrderBook.from_kafka(ticker):
                # Process orderbook updates
                ...
        """
        consumer = AIOKafkaConsumer(
            f"orderbook.{ticker}",
            bootstrap_servers=kafka_bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='latest'
        )
        
        await consumer.start()
        
        try:
            async for msg in consumer:
                # Create OrderBook instance without publishing back to Kafka
                yield cls(msg.value, publish_to_kafka=False, logger=logger)
        finally:
            # Ensure consumer is always stopped, even if an error occurs
            await consumer.stop()

    async def close(self):
        """Clean up resources"""
        if self.producer:
            await self.producer.stop()

    def _update_top_of_book(self) -> None:
        """Update the best prices and sizes for both sides."""
        # Yes/bid side (highest price is best)
        if not self.yes_levels:
            self.best_yes = None
        else:
            price = max(self.yes_levels.keys())
            size = self.yes_levels[price]
            self.best_yes = PriceLevel(price, size)

        # No/ask side (lowest price is best)
        if not self.no_levels:
            self.best_no = None
        else:
            price = min(self.no_levels.keys())
            size = self.no_levels[price]
            self.best_no = PriceLevel(price, size)

    def _update_side(self, side: str, price: float, size_delta: float) -> None:
        """Update quantity at price level for specified side.
        
        Args:
            side: Either 'yes' or 'no'
            price: Price level to update
            size_delta: Change in quantity (positive=increase, negative=decrease)
        """
        if side not in ['yes', 'no']:
            error_msg = "side must be either 'yes' or 'no'"
            self._log_error(error_msg)
            raise ValueError(error_msg)
            
        # Get reference to correct price level dictionary
        levels = self.yes_levels if side == 'yes' else self.no_levels
        current_quantity = levels.get(price, 0)
        new_quantity = current_quantity + size_delta

        self._log_info(f"{side} ${price}: {current_quantity} -> {new_quantity}")
        
        if new_quantity == 0:
            if side == 'yes':
                self.yes_levels.pop(price, None)
            else:
                self.no_levels.pop(price, None)
        elif new_quantity < 0:
            error_msg = "Quantity cannot be negative"
            self._log_error(error_msg)
            raise ValueError(error_msg)
        else:
            if side == 'yes':
                self.yes_levels[price] = new_quantity
            else:
                self.no_levels[price] = new_quantity
            
        self._update_top_of_book()

    def get_book(self, side='yes'):
        """Get consolidated yes book including transformed no orders."""
        yes_bids = self.yes_levels
        no_bids = self.no_levels

        bids = yes_bids if side == 'yes' else no_bids
        alt_bids = no_bids if side == 'yes' else yes_bids
        
        # Transform no bids into equivalent yes offers
        # For each no bid at price p, create a yes offer at price (100-p)
        offers = {
            100 - int(price): quantity 
            for price, quantity in alt_bids.items()
        }

        return {
            'bids': bids,
            'offers': offers
        }

    def get_bbo(self):
        """Get best bid and ask prices."""
        return {
            'bid': self.best_yes,
            'ask': self.best_no
        }

    def _log_error(self, message: str) -> None:
        """Log error message if logger is available."""
        if self.logger:
            self.logger.error(message)
        else:
            print(message)

    def _log_info(self, message: str) -> None:
        """Log info message if logger is available."""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)

if __name__ == "__main__":
    # Example usage
    async def main():
        orderbook_dict = {'market_ticker': 'AAPL', 'no': [[2, 38]], 'yes': [[1, 50]]}
        orderbook = OrderBook(orderbook_dict)
        await orderbook.initialize_producer()

        print("Consuming from Kafka: ")
        async for book in OrderBook.from_kafka('AAPL'):
            print(f"No levels: {book.no_levels}")
            print(f"Yes levels: {book.yes_levels}")
            print(f"Best no: {book.best_no}")
            print(f"Best yes: {book.best_yes}")
            break  # Just show first update

        await orderbook.close()

    asyncio.run(main())