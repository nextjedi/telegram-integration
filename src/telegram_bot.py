"""
Production Telegram Trading Bot
Runs continuously to monitor trading channels and forward calls to API
"""
import asyncio
import datetime
import ssl
import os
import json
import logging
from pathlib import Path

import requests
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# Import our enhanced message parser
from message_parser import enhanced_message_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ssl._create_default_https_context = ssl._create_unverified_context

# Load configuration from environment variables
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
api_endpoint = os.getenv("TRADING_API_ENDPOINT", "https://tip-based-trading.azurewebsites.net/")
session_name = os.getenv("TELEGRAM_SESSION_NAME", "telegram_trading_session")

# Channel IDs from environment or defaults
btst_channel = int(os.getenv("BTST_CHANNEL_ID", "-1001552501322"))
daytrade_channel = int(os.getenv("DAYTRADE_CHANNEL_ID", "-1001752927494"))
univest_channel = int(os.getenv("UNIVEST_CHANNEL_ID", "-1001983880498"))

# Validate required environment variables
if not api_id or not api_hash or not phone_number:
    raise ValueError("Missing required environment variables: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE_NUMBER")

# Check for session file in mounted volume first, then fall back to local
session_paths = [
    f"/app/sessions/{session_name}.session",  # Mounted Azure File Share
    f"{session_name}.session"  # Local fallback
]

session_file_path = None
for path in session_paths:
    if os.path.exists(path):
        session_file_path = path
        logger.info(f"Found session file at: {path}")
        break

if session_file_path and "/app/sessions/" in session_file_path:
    # Copy session file from mounted volume to local writable location
    import shutil
    local_session_path = f"/app/{session_name}.session"
    shutil.copy2(session_file_path, local_session_path)
    logger.info(f"Copied session file to writable location: {local_session_path}")
    client = TelegramClient(session_name, api_id, api_hash)  # Use local copy
elif session_file_path:
    # Use existing local session file
    session_path = session_file_path.replace('.session', '')
    client = TelegramClient(session_path, api_id, api_hash)
    logger.info(f"Using local session file: {session_file_path}")
else:
    # No existing session found, create new one
    client = TelegramClient(session_name, api_id, api_hash)
    logger.info(f"No existing session found, creating new: {session_name}.session")


def is_trading_hours():
    """Check if current time is within trading hours (Mon-Fri 8AM-4PM IST)"""
    now = datetime.datetime.now()
    
    # Check if it's Monday to Friday (0=Monday, 6=Sunday)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check if it's between 8 AM and 4 PM
    if now.hour < 8 or now.hour >= 16:
        return False
        
    return True


async def handleMessages(m, group):
    """
    Enhanced message handler using the new message parser
    Only processes messages during trading hours
    """
    try:
        # Check if we're in trading hours
        if not is_trading_hours():
            logger.info(f"Outside trading hours, skipping message from {group}")
            return
        
        # Use the enhanced message processor
        call_data = enhanced_message_processor(m)
        
        if not call_data:
            # Not a trading call, skip silently
            return
        
        logger.info(f"TRADING CALL DETECTED - {call_data['type'].upper()}")
        logger.info(f"Time: {call_data['timestamp']}")
        logger.info(f"Confidence: {call_data['confidence']}%")
        logger.info(f"Group: {group}")
        
        if call_data['type'] == 'image':
            await handle_image_call(m, call_data, group)
        elif call_data['type'] == 'text':
            await handle_text_call(m, call_data, group)
        
    except Exception as e:
        logger.error(f"Error in handleMessages: {e}")
        if m.text:
            logger.error(f"Message text: {m.text[:100]}...")


async def handle_image_call(message_obj, call_data, group):
    """Handle image-based trading calls"""
    try:
        if call_data['confidence'] >= 70:
            logger.info("HIGH CONFIDENCE IMAGE CALL")
            
            # If the image has a text caption with trading info, process it
            data = call_data.get('data', {})
            if not data.get('requires_ocr'):
                # Caption contained parseable trading info
                await process_trading_data(data, group, message_obj)
            else:
                # Image requires OCR - log for manual review
                logger.info("Image call requires OCR - manual review recommended")
        else:
            logger.info(f"Low confidence image call ({call_data['confidence']}%), skipping...")
            
    except Exception as e:
        logger.error(f"Error handling image call: {e}")


async def handle_text_call(message_obj, call_data, group):
    """Handle text-based trading calls"""
    try:
        data = call_data.get('data', {})
        
        if call_data['confidence'] >= 70:
            logger.info("HIGH CONFIDENCE TEXT CALL")
            await process_trading_data(data, group, message_obj)
        elif call_data['confidence'] >= 50:
            logger.info("MEDIUM CONFIDENCE TEXT CALL")
            await process_trading_data(data, group, message_obj, is_medium_confidence=True)
        else:
            logger.info(f"Low confidence text call ({call_data['confidence']}%), skipping...")
            
    except Exception as e:
        logger.error(f"Error handling text call: {e}")


async def process_trading_data(data, group, message_obj, is_medium_confidence=False):
    """Process and send trading call data to API"""
    try:
        # Validate essential data
        if not data.get('strike') or not data.get('trigger_price'):
            logger.error("Incomplete trading data, skipping API call")
            return
        
        # Prepare trigger price (handle ranges like "50-60")
        trigger_str = str(data.get('trigger_price', '0'))
        trigger = float(trigger_str.split('-')[0]) if '-' in trigger_str else float(trigger_str)
        
        # Use smart stop loss and target if available, otherwise calculate basic ones
        if data.get('smart_sl') and data.get('smart_target'):
            stop_loss = data['smart_sl']
            target = data['smart_target']
        else:
            # Fallback to basic calculation
            stop_loss = max(0.5, trigger - 5) if trigger > 5 else trigger * 0.5
            target = trigger + 10
        
        # Prepare API data
        api_data = {
            "instrument": {
                "name": data.get('instrument', 'BANKNIFTY'),
                "strike": data.get('strike'),
                "instrumentType": data.get('option_type', 'PE')
            },
            "price": trigger,
            "stopLoss": stop_loss,
            "target": target,
            "confidence": data.get('confidence', 0),
            "type": group,
            "parser_version": "enhanced_v1"
        }
        
        # Log detailed call information
        logger.info(f"Instrument: {api_data['instrument']['name']}")
        logger.info(f"Strike: {api_data['instrument']['strike']}")
        logger.info(f"Type: {api_data['instrument']['instrumentType']}")
        logger.info(f"Entry: {api_data['price']}")
        logger.info(f"Stop Loss: {api_data['stopLoss']}")
        logger.info(f"Target: {api_data['target']}")
        
        if not is_medium_confidence:
            # Send to API for high confidence calls
            try:
                logger.info("Sending to trading API...")
                response = requests.post(url=api_endpoint + "tip", json=api_data, timeout=10)
                logger.info(f"API Response: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info("Trading call successfully sent to API")
                else:
                    logger.warning(f"API returned status code: {response.status_code}")
                    
            except requests.RequestException as e:
                logger.error(f"API request failed: {e}")
        else:
            # For medium confidence, just log but don't send to API
            logger.info("Medium confidence call logged, not sent to API")
            
    except Exception as e:
        logger.error(f"Error processing trading data: {e}")
        logger.error(f"Data: {data}")


# Event handlers for each channel
@client.on(events.NewMessage(chats=daytrade_channel))
async def trade_daytrade(event):
    await handleMessages(event.message, "DAY")


@client.on(events.NewMessage(chats=btst_channel))
async def trade_btst(event):
    await handleMessages(event.message, "BTST")


@client.on(events.NewMessage(chats=univest_channel))
async def trade_univest(event):
    await handleMessages(event.message, "UNIVEST")


async def main():
    """Main function to start the bot"""
    try:
        await client.start(phone=lambda: phone_number)
        logger.info("Connected to Telegram successfully!")
        logger.info(f"Monitoring channels: DAY({daytrade_channel}), BTST({btst_channel}), UNIVEST({univest_channel})")
        logger.info("Trading hours: Monday-Friday 8:00 AM - 4:00 PM IST")
        logger.info("Bot is running... Press Ctrl+C to stop")
        
        # Keep the client running
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise


if __name__ == "__main__":
    # Run the bot
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())