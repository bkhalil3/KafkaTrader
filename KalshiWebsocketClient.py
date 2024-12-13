import json
import websockets
import asyncio
import requests
from typing import List, Optional, Dict, Any
import os

class KalshiWebsocketClient:
    def __init__(self, email: str, password: str, env: str = "prod"):
        """Initialize the Kalshi WebSocket client.
        
        Args:
            email: Your Kalshi account email
            password: Your Kalshi account password
            env: Either "prod" or "demo" to determine which environment to connect to
        """
        self.email = email
        self.password = password
        self.env = env
        self.command_id = 1
        self.subscriptions = {}
        
        # Set API endpoints based on environment
        if env == "prod":
            self.rest_api = "https://trading-api.kalshi.com/trade-api/v2"
            self.ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
            # self.election_ws_url = "wss://api.elections.kalshi.com/trade-api/v2"
        else:  # demo environment
            self.rest_api = "https://demo-api.kalshi.co/trade-api/v2"
            self.ws_url = "wss://demo-api.kalshi.co/trade-api/ws/v2"
            
        self.token = None
        self.websocket = None

    async def login(self) -> None:
        """Log in to Kalshi and get authentication token."""
        login_url = f"{self.rest_api}/login"
        payload = {
            "email": self.email,
            "password": self.password
        }
        
        response = requests.post(login_url, json=payload)
        response.raise_for_status()
        self.token = response.json()["token"]

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        if not self.token:
            await self.login()
            
        headers = {"Authorization": f"Bearer {self.token}"}
        self.websocket = await websockets.connect(self.ws_url, extra_headers=headers)

    async def subscribe_orderbook(self, market_tickers: List[str]) -> None:
        """Subscribe to orderbook updates for specific markets.
        
        Args:
            market_tickers: List of market tickers to subscribe to
        """
        command = {
            "id": self.command_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["orderbook_delta"],
                "market_tickers": market_tickers
            }
        }
        await self.websocket.send(json.dumps(command))
        self.command_id += 1

    async def subscribe_ticker(self, market_tickers: Optional[List[str]] = None) -> None:
        """Subscribe to ticker updates.
        
        Args:
            market_tickers: Optional list of market tickers. If None, subscribes to all markets.
        """
        command = {
            "id": self.command_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }
        if market_tickers:
            command["params"]["market_tickers"] = market_tickers
            
        await self.websocket.send(json.dumps(command))
        self.command_id += 1

    async def subscribe_trades(self, market_tickers: Optional[List[str]] = None) -> None:
        """Subscribe to trade updates.
        
        Args:
            market_tickers: Optional list of market tickers. If None, subscribes to all markets.
        """
        command = {
            "id": self.command_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["trade"]
            }
        }
        if market_tickers:
            command["params"]["market_tickers"] = market_tickers
            
        await self.websocket.send(json.dumps(command))
        self.command_id += 1

    async def subscribe_fills(self, market_ticker: Optional[str] = None, 
                            market_tickers: Optional[List[str]] = None) -> None:
        """Subscribe to fill updates.
        
        Args:
            market_ticker: Optional single market ticker
            market_tickers: Optional list of market tickers
        """
        command = {
            "id": self.command_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["fill"]
            }
        }
        if market_ticker:
            command["params"]["market_ticker"] = market_ticker
        elif market_tickers:
            command["params"]["market_tickers"] = market_tickers
            
        await self.websocket.send(json.dumps(command))
        self.command_id += 1

    async def subscribe_market_lifecycle(self) -> None:
        """Subscribe to market lifecycle events."""
        command = {
            "id": self.command_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["market_lifecycle"]
            }
        }
        await self.websocket.send(json.dumps(command))
        self.command_id += 1

    async def unsubscribe(self, subscription_ids: List[int]) -> None:
        """Unsubscribe from channels.
        
        Args:
            subscription_ids: List of subscription IDs to unsubscribe from
        """
        command = {
            "id": self.command_id,
            "cmd": "unsubscribe",
            "params": {
                "sids": subscription_ids
            }
        }
        await self.websocket.send(json.dumps(command))
        self.command_id += 1

    async def update_subscription(self, subscription_id: int, 
                                market_tickers: List[str], 
                                action: str) -> None:
        """Update an existing subscription.
        
        Args:
            subscription_id: ID of subscription to update
            market_tickers: List of market tickers to add or remove
            action: Either "add_markets" or "delete_markets"
        """
        command = {
            "id": self.command_id,
            "cmd": "update_subscription",
            "params": {
                "sids": [subscription_id],
                "market_tickers": market_tickers,
                "action": action
            }
        }
        await self.websocket.send(json.dumps(command))
        self.command_id += 1

    async def listen(self, callback) -> None:
        """Listen for messages and process them with callback function.
        
        Args:
            callback: Function that takes a message dictionary as argument
        """
        try:
            while True:
                message = await self.websocket.recv()
                await callback(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed. Attempting to reconnect...")
            await self.connect()

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()

# Example usage
async def example_callback(message: Dict[str, Any]) -> None:
    print(f"Received message: {message}")

async def main():
    # Initialize client
    client = KalshiWebsocketClient(
        email=os.getenv('KALSHI_PROD_EMAIL'),
        password=os.getenv('KALSHI_PROD_PASSWORD'),
        env="prod"
    )
    
    try:
        # Connect to websocket
        await client.connect()
        
        # Subscribe to various channels
        await client.subscribe_orderbook(["KXHIGHNY-24NOV05-B71.5"])
        await client.subscribe_ticker(["KXHIGHNY-24NOV05-B71.5"])
        await client.subscribe_trades(["KXHIGHNY-24NOV05-B71.5"])
        #await client.subscribe_fills()
        await client.subscribe_market_lifecycle()
        
        # Listen for messages
        await client.listen(example_callback)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
