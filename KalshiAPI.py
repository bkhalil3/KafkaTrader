import os
import kalshi_python
from kalshi_python.models import *

prod_config = kalshi_python.Configuration()
demo_config = kalshi_python.Configuration()

# Comment the line below to use production
# config.host = 'https://trading-api.kalshi.com/trade-api/v2'
prod_config.host = 'https://api.elections.kalshi.com/trade-api/v2'
demo_config.host = 'https://demo-api.kalshi.co/trade-api/v2'

# Load email and password from environment variables
prod_email = os.getenv('KALSHI_PROD_EMAIL')
prod_password = os.getenv('KALSHI_PROD_PASSWORD')
demo_email = os.getenv('KALSHI_DEMO_EMAIL')
demo_password = os.getenv('KALSHI_DEMO_PASSWORD')

# Create an API configuration passing your credentials.
# Use this if you want the kalshi_python sdk to manage the authentication for you.
prod_kalshi_api = kalshi_python.ApiInstance(
    email=prod_email,
    password=prod_password,
    configuration=prod_config,
)

demo_kalshi_api = kalshi_python.ApiInstance(
    email=demo_email,
    password=demo_password,
    configuration=demo_config,
)

kalshi_api = prod_kalshi_api

if __name__ == "__main__":
    prod_kalshi_api.email