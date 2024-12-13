import logging
from MarketMonitor import monitor_event
from Series import event_list
from OrderBook import OrderBook
from OrderManagementSystem import OrderManagementSystem, Order
from KalshiAPI import kalshi_api

oms = OrderManagementSystem(kalshi_api)

# If the best yes price is between 5 and 20 for any orderbook in this event, 
# send a buy order for 10 no-contracts at (at most) the best yes price + 5 cents
#
# WARNING: This strategy is not profitable and is only for demonstration purposes
class TestStrategy:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def update(self, orderbook: OrderBook, updates: int, timestamp: float):
        best_yes = orderbook.best_yes # Check if there is a best yes

        if best_yes and best_yes.price > 5 and best_yes.price < 20:
            print(f"Sending buy order for {orderbook.ticker}:no at limit price {best_yes.price + 5} for 10 contracts")
            self.logger.info(f"Sending buy order for {orderbook.ticker}:no at limit price {orderbook.best_yes.price + 5} for 10 contracts")

            oms.send_order(Order(
                ticker=orderbook.ticker,
                action="buy",
                type="limit",
                no_price=orderbook.best_yes.price + 5,
                amount=10,
                side="no"
            ))

async def main(logger: logging.Logger, args):
    if args.ticker:
        event = args.ticker
    else:
        event = event_list[0]

    logger.info(f"Starting test strategy with event: {event}")
    await monitor_event(event, TestStrategy(logger).update, logger)