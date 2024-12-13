import asyncio
from dataclasses import dataclass, field
from kalshi_python.models import CreateOrderRequest
from typing import Optional
import uuid

@dataclass
class Order:
    ticker: str
    action: str  # 'buy' or 'sell'
    type: str    # 'limit' or 'market'
    amount: int     # Number of contracts
    side: str       # 'yes' or 'no'
    yes_price: Optional[int] = None  # Price in cents
    no_price: Optional[int] = None    # Price in cents
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tags: Optional[dict] = None # Additional metadata

    def __post_init__(self):
        if (self.yes_price is not None and self.no_price is not None):
            raise ValueError("An order can only have either a yes_price or a no_price, not both.")

class OrderManagementSystem:
    def __init__(self, kalshi_api):
        self.live_orders = {}  # Dictionary to track live orders
        self.kalshi_api = kalshi_api  # Instance of the Kalshi API

    async def send_order(self, order: Order):
        if not self.kalshi_api.get_exchange_status().trading_active:
            raise Exception("Market is not actively trading")
        if not self.validate_order(order):
            raise ValueError("Invalid order")

        # Run risk checks before sending
        await self.run_risk_checks(order)
        market_response = await self.send_to_market(order)
        if market_response.get('order_id'):
            self.live_orders[order.id] = order
        else:
            raise Exception("Failed to send order to market")

    async def send_to_market(self, order: Order):
        order_request = CreateOrderRequest(
            ticker=order.ticker,
            action=order.action,
            type=order.type,
            yes_price=order.yes_price,
            no_price=order.no_price,
            count=order.amount,
            client_order_id=order.id,
            side=order.side
        )
        response = self.kalshi_api.create_order(order_request)
        return response

    async def cancel_in_market(self, order_id: str):
        response = self.kalshi_api.cancel_order(order_id)
        return response

    async def update_order(self, order_id: str, new_order_details: dict):
        if order_id in self.live_orders:
            # Update the order with new details
            order = self.live_orders[order_id]
            order.amount = new_order_details.get('amount', order.amount)
            order.yes_price = new_order_details.get('yes_price', order.yes_price)
            order.no_price = new_order_details.get('no_price', order.no_price)
            order.action = new_order_details.get('action', order.action)
            order.type = new_order_details.get('type', order.type)

            # Optionally, send the updated order to the market
            market_response = await self.send_to_market(order)
            return market_response
        else:
            raise KeyError("Order ID not found")

    async def run_risk_checks(self, order: Order):
        # Pseudo-code for risk checks
        if await self.check_market_conditions(order):
            if await self.check_account_balance(order):
                return True
        raise Exception("Risk checks failed")

    async def cancel_order(self, order_id: str):
        if order_id in self.live_orders:
            market_response = await self.cancel_in_market(order_id)
            if market_response.success:
                del self.live_orders[order_id]  # Remove from live orders
            else:
                raise Exception("Failed to cancel order in market")
        else:
            raise KeyError("Order ID not found")

    async def get_live_orders(self):
        # Return a list of live orders
        return list(self.live_orders.values())

    async def check_market_conditions(self, order: Order):
        # Simulate checking market conditions
        return await asyncio.sleep(1, result=True)

    async def check_account_balance(self, order: Order):
        # Simulate checking account balance
        return await asyncio.sleep(1, result=True)

    def validate_order(self, order: Order):
        # Basic validation logic for the order
        return hasattr(order, 'id') and hasattr(order, 'amount') and order.amount > 0


async def main():
    from KalshiAPI import kalshi_api
    oms = OrderManagementSystem(kalshi_api)

    order = Order(
        ticker="KXHIGHNY-24NOV15-B58.5", 
        action="buy", 
        type="limit", 
        yes_price=100, 
        amount=1, 
        side="yes"
    )

    await oms.send_order(order)
     
    print(oms.get_live_orders())

if __name__ == "__main__":
    asyncio.run(main())
