# KafkaTrader: Automated Market Interaction Framework
**KafkaTrader** is a Python-based framework designed for algorithmic trading and data monitoring in Kalshi markets. It connects to Kalshi's API, processes market data in real-time, and enables users to implement and test custom trading strategies.

This project provides tools to subscribe to market events, manage orders and positions, and experiment with strategies while leveraging Kafka for data streaming.

---

## Features
- **Real-time Market Data Processing**: Subscribe to Kalshi events and stream them into Kafka for analysis.
- **Customizable Strategies**: Develop and test strategies with plug-and-play support.
- **Order Management**: Track positions and active orders across strategies.
- **Demo & Production Modes**: Seamlessly switch between environments for testing and live execution.

---

## Requirements
- Python 3.10+
- Kalshi API key (prod and/or demo)
- Running Kafka server ([Setup Kafka](https://kafka.apache.org/quickstart))
    - Assumes default port of 9092

---

## Installation
1. Clone the repository:
```bash
git clone <repository_url>
cd KafkaTrader
```

2. install the required packages
```bash
pip install -r requirements.txt
```

---

## Configuration
Ensure the following environment variables are set:

| Variable                | Purpose                  |
|-------------------------|--------------------------|
| `KALSHI_PROD_EMAIL`     | Production API email     |
| `KALSHI_PROD_PASSWORD`  | Production API password  |
| `KALSHI_DEMO_EMAIL`     | Demo API email           |
| `KALSHI_DEMO_PASSWORD`  | Demo API password        |
Switch between **production** and **demo** environments by updating the `kalshi_api variable` in `KalshiAPI.py` to either `prod_kalshi_api` or `demo_kalshi_api`.

---

## Usage
### Available Components
1. **MarketDataService**
Streams Kalshi market data events into Kafka.

2. **MarketMonitor**
Reads data from Kafka and forwards it to handlers. Example handler: `print_orderbook`, which displays the current order book.

3. **User Strategies**
Create custom strategies to act on market data events. Example: `TestStrategy` sends a market order based on predefined conditions.

4. **OrderManagementSystem**
Manages open orders and tracks positions across strategies.

## Running the System
Run the main script and specify components using the `--components` flag:
```bash
python run.py --components monitor strategy --ticker POPVOTEMOVSMALLER-24
```
- `monitor`: Launches the `MarketMonitor` with the print_orderbook` handler.
- `strategy`: Activates the `TestStrategy`.
- `--ticker`: Specifies the market to subscribe to. Omit this flag to use the predefined `market_list` in `Series.py`.

---

### Example Usage
To monitor a market and execute a test strategy:
```bash
python run.py --components monitor strategy --ticker POPVOTEMOVSMALLER-24
```

---

## Custom Strategies
Strategies are modular and easy to create. Implement a new strategy by subclassing and overriding methods in the `Strategy` base class. For example, modify the `TestStrategy` to define your conditions and trading logic.

## Contribution & Feedback
Contributions are welcome! Feel free to fork the repository and submit a pull request.

For feedback or issues, please open a ticket in the Issues section of the repository.
