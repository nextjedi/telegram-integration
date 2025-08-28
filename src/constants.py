"""
Configuration constants for Telegram Trading Bot
"""

# Telegram Channel IDs
BTST_CHANNEL_ID = -1001552501322
DAYTRADE_CHANNEL_ID = -1001752927494  
UNIVEST_CHANNEL_ID = -1001983880498

# API Configuration
TRADING_API_ENDPOINT = "https://tip-based-trading.azurewebsites.net/tip"

# Channel mapping for easy reference
CHANNELS = {
    'BTST': BTST_CHANNEL_ID,
    'DAY': DAYTRADE_CHANNEL_ID,
    'UNIVEST': UNIVEST_CHANNEL_ID
}

# Trading session configuration
TRADING_HOURS = {
    'START_TIME': '09:15',  # IST
    'END_TIME': '15:30',    # IST
    'TIMEZONE': 'Asia/Kolkata'
}

# Parser configuration
CONFIDENCE_THRESHOLDS = {
    'HIGH': 70,
    'MEDIUM': 50,
    'LOW': 40
}