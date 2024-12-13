from kalshi_python.models import *
from KalshiAPI import kalshi_api
from pprint import pprint


series = [
    "KXHIGHAUS",
    "KXHIGHMIA",
    "KXHIGHNY",
    "KXHIGHCHI"
]

events = {s: kalshi_api.get_events(series_ticker=s, status="open").events for s in series}

event_list = [e.event_ticker for s in events.values() for e in s]

markets = {e: kalshi_api.get_markets(event_ticker=e).markets for e in event_list}

market_list = [m.ticker for s in markets.values() for m in s]

if __name__ == "__main__":
    pprint(markets)
