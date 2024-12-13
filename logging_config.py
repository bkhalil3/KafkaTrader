import os
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('logs/market_data', exist_ok=True)
os.makedirs('logs/monitor', exist_ok=True)
os.makedirs('logs/strategies', exist_ok=True)

# Generate timestamp for log files
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'simple': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'market_data_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': f'logs/market_data/{TIMESTAMP}.log',
            'mode': 'a'
        },
        'monitor_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': f'logs/monitor/{TIMESTAMP}.log',
            'mode': 'a'
        },
        'strategy_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': f'logs/strategies/{TIMESTAMP}.log',
            'mode': 'a'
        }
    },
    'loggers': {
        'MarketData': {
            'handlers': ['market_data_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'Monitor': {
            'handlers': ['console', 'monitor_file'],
            'level': 'DEBUG', 
            'propagate': False
        },
        'Strategies': {
            'handlers': ['strategy_file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
} 
