import asyncio
import datetime
import ssl
import os
import json
from pathlib import Path

import requests
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# Import our enhanced message parser and constants
from message_parser import enhanced_message_processor
from constants import BTST_CHANNEL_ID, DAYTRADE_CHANNEL_ID, UNIVEST_CHANNEL_ID, TRADING_API_ENDPOINT

# Create test data directories if they don't exist
Path("src/test_data/raw_messages").mkdir(parents=True, exist_ok=True)
Path("src/test_data/images").mkdir(parents=True, exist_ok=True)
Path("src/test_data/parsing_results").mkdir(parents=True, exist_ok=True)

ssl._create_default_https_context = ssl._create_unverified_context

# Load configuration from environment variables
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
session_name = os.getenv("TELEGRAM_SESSION_NAME", "session_name")

# Use constants for channel IDs and API endpoint
btst_channel = BTST_CHANNEL_ID
daytrade_channel = DAYTRADE_CHANNEL_ID
univest_channel = UNIVEST_CHANNEL_ID
api_endpoint = TRADING_API_ENDPOINT

# Validate required environment variables
if not api_id or not api_hash or not phone_number:
    raise ValueError("Missing required environment variables: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE_NUMBER")

# Use session file from mounted Azure File Share
session_path = f"/app/sessions/{session_name}"
print(f"Using session file: {session_path}")

client = TelegramClient(session_path, api_id, api_hash)

# client.start() will be called inside async context


async def handleMessages(m, group):
    """
    Enhanced message handler using the new message parser
    Supports both text and image-based trading calls
    Saves raw messages and parsing results for testing
    """
    try:
        # Save raw message data for testing (only for daytrade and univest groups)
        if group.upper() in ['DAY', 'UNIVEST']:
            await save_raw_message(m, group)
            # Save image if present
            if m.media:
                await save_message_image(m, group)
        
        # Use the enhanced message processor
        call_data = enhanced_message_processor(m)
        
        # Save parsing results for testing
        if group.upper() in ['DAY', 'UNIVEST']:
            await save_parsing_result(m, call_data, group)
        
        if not call_data:
            # Not a trading call, skip silently
            return
        
        print(f"\n{'='*50}")
        print(f"[CALL] TRADING CALL DETECTED - {call_data['type'].upper()}")
        print(f"[TIME] {call_data['timestamp']}")
        print(f"[CONF] Confidence: {call_data['confidence']}%")
        print(f"[GROUP] {group}")
        
        if call_data['type'] == 'image':
            await handle_image_call(m, call_data, group)
        elif call_data['type'] == 'text':
            await handle_text_call(m, call_data, group)
        
    except Exception as e:
        print(f"[ERROR] Error in handleMessages: {e}")
        if m.text:
            print(f"[TEXT] Message text: {m.text[:100]}...")


async def handle_image_call(message_obj, call_data, group):
    """Handle image-based trading calls"""
    try:
        if call_data['confidence'] >= 80:
            print("[IMG] HIGH CONFIDENCE IMAGE CALL")
            
            # Save image to test data directory for testing (daytrade and univest)
            if group.upper() in ['DAY', 'UNIVEST']:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                test_filename = f"src/test_data/images/call_{call_data['message_id']}_{group.lower()}_{timestamp}.jpg"
                await client.download_media(message_obj, test_filename)
                print(f"[TEST] Trading call image saved: {test_filename}")
            
            # Create directory for trading images if it doesn't exist
            os.makedirs("trading_images", exist_ok=True)
            
            # Download the image
            filename = f"trading_images/call_{call_data['message_id']}_{group.lower()}.jpg"
            await client.download_media(message_obj, filename)
            print(f"[SAVE] Image saved: {filename}")
            
            # If the image has a text caption with trading info, process it
            data = call_data.get('data', {})
            if not data.get('requires_ocr'):
                # Caption contained parseable trading info
                await process_trading_data(data, group, message_obj)
            else:
                # Image requires OCR - for now, just alert users
                alert_msg = (f"HIGH CONFIDENCE IMAGE CALL DETECTED\n"
                           f"Confidence: {call_data['confidence']}%\n" 
                           f"Time: {call_data['timestamp']}\n"
                           f"Saved as: {filename}\n"
                           f"Manual review recommended")
                
                # await send_message_forward(group, alert_msg)  # Commented out
                print("[ALERT] Image call alert would be sent to users")
        else:
            print(f"[WARN] Low confidence image call ({call_data['confidence']}%), skipping...")
            
    except Exception as e:
        print(f"[ERROR] Error handling image call: {e}")


async def handle_text_call(message_obj, call_data, group):
    """Handle text-based trading calls"""
    try:
        data = call_data.get('data', {})
        
        if call_data['confidence'] >= 70:
            print("[TEXT] HIGH CONFIDENCE TEXT CALL")
            await process_trading_data(data, group, message_obj)
        elif call_data['confidence'] >= 50:
            print("[TEXT] MEDIUM CONFIDENCE TEXT CALL")
            # For medium confidence, still process but with lower priority
            await process_trading_data(data, group, message_obj, is_medium_confidence=True)
        else:
            print(f"[WARN] Low confidence text call ({call_data['confidence']}%), skipping...")
            
    except Exception as e:
        print(f"[ERROR] Error handling text call: {e}")


async def process_trading_data(data, group, message_obj, is_medium_confidence=False):
    """Process and send trading call data to API and users"""
    try:
        # Validate essential data
        if not data.get('strike') or not data.get('trigger_price'):
            print("[ERROR] Incomplete trading data, skipping API call")
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
        
        # Print detailed call information
        print(f"[INST] Instrument: {api_data['instrument']['name']}")
        print(f"[STRK] Strike: {api_data['instrument']['strike']}")
        print(f"[TYPE] Type: {api_data['instrument']['instrumentType']}")
        print(f"[ENTR] Entry: {api_data['price']}")
        print(f"[SL] Stop Loss: {api_data['stopLoss']}")
        print(f"[TGT] Target: {api_data['target']}")
        
        if not is_medium_confidence:
            # Send to API for high confidence calls (COMMENTED OUT FOR TESTING)
            print("[API] Would send to API (commented out for testing)...")
            print(f"[DATA] API Data: {api_data}")
            
            try:
                print("📤 Sending to API...")
                response = requests.post(url=api_endpoint + "tip", json=api_data, timeout=10)
                print(f"✅ API Response: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ Trading call successfully sent to API")
                else:
                    print(f"⚠️ API returned status code: {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"❌ API request failed: {e}")
        else:
            # For medium confidence, just log but don't send to API
            print("[LOG] Medium confidence call logged, not sent to API")
            
    except Exception as e:
        print(f"[ERROR] Error processing trading data: {e}")
        print(f"[DATA] Data: {data}")


# Keep the old method as backup (renamed)
async def handleMessages_old_backup(m, group):
    """
    Old method kept as backup - DO NOT USE
    """
    # ... (old implementation commented out for reference)
    pass





# get message from bank nifty (daytrade)
@client.on(events.NewMessage(chats=daytrade_channel))
async def trade(event):
    print(event.message.text)
    await handleMessages(event.message, "DAY")


# get message from BTST
@client.on(events.NewMessage(chats=btst_channel))
async def trade_btst(event):
    await handleMessages(event.message, "BTST")


# get message from univest
@client.on(events.NewMessage(chats=univest_channel))
async def trade_univest(event):
    print(f"[UNIVEST] Message: {event.message.text}")
    await handleMessages(event.message, "UNIVEST")


def write_detected_calls_to_file(detected_calls, group):
    """Write all detected trading calls to a formatted text file"""
    import json
    from datetime import datetime
    
    filename = "detected_trading_calls.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DETECTED TRADING CALLS REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Groups: {group}\n")
        f.write(f"Total Calls Detected: {len(detected_calls)}\n")
        f.write("=" * 80 + "\n\n")
        
        if not detected_calls:
            f.write("No trading calls detected in the analyzed messages.\n")
            return
        
        for idx, call in enumerate(detected_calls, 1):
            f.write(f"CALL #{idx}\n")
            f.write("-" * 60 + "\n")
            f.write(f"Message ID: {call['message_id']}\n")
            f.write(f"Timestamp: {call['timestamp']}\n")
            f.write(f"Call Type: {call['type'].upper()}\n")
            f.write(f"Confidence: {call['confidence']}%\n")
            f.write(f"Has Media: {'Yes' if call['has_media'] else 'No'}\n")
            
            # Extract trading details if available
            data = call.get('data', {})
            if data:
                f.write("\nTRADING DETAILS:\n")
                if data.get('instrument'):
                    f.write(f"  Instrument: {data.get('instrument', 'N/A')}\n")
                if data.get('strike'):
                    f.write(f"  Strike: {data.get('strike', 'N/A')}\n")
                if data.get('option_type'):
                    f.write(f"  Option Type: {data.get('option_type', 'N/A')}\n")
                if data.get('trigger_price'):
                    f.write(f"  Entry Price: {data.get('trigger_price', 'N/A')}\n")
                if data.get('stop_loss'):
                    f.write(f"  Stop Loss: {data.get('stop_loss', 'N/A')}\n")
                if data.get('target'):
                    f.write(f"  Target: {data.get('target', 'N/A')}\n")
                if data.get('smart_sl'):
                    f.write(f"  Smart SL: {data.get('smart_sl', 'N/A')}\n")
                if data.get('smart_target'):
                    f.write(f"  Smart Target: {data.get('smart_target', 'N/A')}\n")
            
            # Add raw message text (if any)
            if call['type'] == 'text' and call.get('raw_text'):
                f.write("\nRAW MESSAGE:\n")
                try:
                    f.write(f"  {call['raw_text']}\n")
                except:
                    f.write("  [Contains special characters that cannot be displayed]\n")
            elif call['type'] == 'image':
                f.write("\nIMAGE CALL:\n")
                if data.get('caption'):
                    try:
                        f.write(f"  Caption: {data.get('caption', 'No caption')}\n")
                    except:
                        f.write("  Caption: [Contains special characters]\n")
                if data.get('message_id'):
                    f.write(f"  Image saved as: trading_images/call_{data['message_id']}_day.jpg\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
        
        # Add summary statistics
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 60 + "\n")
        
        # Count by type
        text_calls = sum(1 for c in detected_calls if c['type'] == 'text')
        image_calls = sum(1 for c in detected_calls if c['type'] == 'image')
        
        f.write(f"Text-based calls: {text_calls}\n")
        f.write(f"Image-based calls: {image_calls}\n")
        
        # Average confidence
        if detected_calls:
            avg_confidence = sum(c['confidence'] for c in detected_calls) / len(detected_calls)
            f.write(f"Average confidence: {avg_confidence:.1f}%\n")
        
        # Count by confidence level
        high_conf = sum(1 for c in detected_calls if c['confidence'] >= 70)
        med_conf = sum(1 for c in detected_calls if 50 <= c['confidence'] < 70)
        low_conf = sum(1 for c in detected_calls if c['confidence'] < 50)
        
        f.write(f"\nConfidence Distribution:\n")
        f.write(f"  High (>=70%): {high_conf}\n")
        f.write(f"  Medium (50-69%): {med_conf}\n")
        f.write(f"  Low (<50%): {low_conf}\n")
    
    print(f"\n[FILE] Detected trading calls written to: {filename}")


async def save_raw_message(message_obj, group):
    """Save raw message data to file for testing purposes"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"src/test_data/raw_messages/{group.lower()}_{message_obj.id}_{timestamp}.json"
        
        message_data = {
            'id': message_obj.id,
            'date': str(message_obj.date),
            'text': message_obj.text,
            'has_media': bool(message_obj.media),
            'media_type': str(type(message_obj.media).__name__) if message_obj.media else None,
            'group': group,
            'channel_id': message_obj.peer_id.channel_id if hasattr(message_obj.peer_id, 'channel_id') else None,
            'saved_at': timestamp
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(message_data, f, indent=2, ensure_ascii=False)
        
        print(f"[TEST] Raw message saved: {filename}")
        
    except Exception as e:
        print(f"[ERROR] Failed to save raw message: {e}")


async def save_message_image(message_obj, group):
    """Save message image to test data directory"""
    try:
        if message_obj.media:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"src/test_data/images/msg_{message_obj.id}_{group.lower()}_{timestamp}.jpg"
            await client.download_media(message_obj, filename)
            print(f"[TEST] Message image saved: {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to save message image: {e}")


async def save_parsing_result(message_obj, call_data, group):
    """Save parsing results to file for testing purposes"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"src/test_data/parsing_results/{group.lower()}_{message_obj.id}_{timestamp}.json"
        
        parsing_result = {
            'message_id': message_obj.id,
            'message_text': message_obj.text,
            'has_media': bool(message_obj.media),
            'media_type': str(type(message_obj.media).__name__) if message_obj.media else None,
            'group': group,
            'parsing_result': call_data,
            'is_trading_call': bool(call_data),
            'confidence': call_data.get('confidence', 0) if call_data else 0,
            'parsed_at': timestamp,
            'message_date': str(message_obj.date)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(parsing_result, f, indent=2, ensure_ascii=False)
        
        print(f"[TEST] Parsing result saved: {filename}")
        
    except Exception as e:
        print(f"[ERROR] Failed to save parsing result: {e}")


async def main():
    try:
        await client.start(phone=lambda: phone_number)
        print("Connected to Telegram successfully!")
    except Exception as e:
        print(f"Error connecting: {e}")
        return
    
    print("\n" + "="*60)
    print("TESTING ENHANCED MESSAGE PARSER ON RECENT MESSAGES")
    print("="*60)
    
    # Get recent messages from daytrade channel and test parsing
    print("\n[FETCH] Fetching recent messages from daytrade channel...")
    daytrade_entity = await client.get_entity(PeerChannel(daytrade_channel))
    recent_messages = await client.get_messages(daytrade_entity, limit=1000)  # Get more messages for better analysis
    
    print(f"[PROC] Processing {len(recent_messages)} recent messages from daytrade...\n")
    
    # Also fetch from univest for comparison
    print("\n[FETCH] Fetching recent messages from univest channel...")
    univest_entity = await client.get_entity(PeerChannel(univest_channel))
    univest_messages = await client.get_messages(univest_entity, limit=500)
    
    print(f"[PROC] Processing {len(univest_messages)} recent messages from univest...\n")
    
    # Combine messages for processing
    all_messages = [(msg, 'DAY') for msg in recent_messages] + [(msg, 'UNIVEST') for msg in univest_messages]
    print(f"[TOTAL] Processing {len(all_messages)} total messages from both channels...\n")
    
    trading_calls_found = 0
    detected_calls = []  # Store all detected calls
    
    for i, (msg, group) in enumerate(all_messages, 1):
        print(f"\n--- Message {i} ({group}) ---")
        print(f"[TIME] {msg.date}")
        
        # Show message content (handle encoding issues)
        try:
            if msg.message:
                preview = msg.message[:100] if len(msg.message) > 100 else msg.message
                print(f"[TEXT] {preview}")
            else:
                print(f"[TEXT] [No text content]")
        except:
            print(f"[TEXT] [Contains special characters]")
        
        # Check if it has media
        if msg.media:
            print(f"[MEDIA] Yes")
        
        # Test our enhanced parser
        print(f"[TEST] Testing parser...")
        await handleMessages(msg, group)
        
        # Check if it was detected as a trading call
        call_data = enhanced_message_processor(msg)
        if call_data:
            trading_calls_found += 1
            # Store detailed call information
            call_info = {
                'message_id': msg.id,
                'timestamp': str(msg.date),
                'type': call_data['type'],
                'confidence': call_data['confidence'],
                'data': call_data.get('data', {}),
                'raw_text': msg.message[:200] if msg.message else 'No text',
                'has_media': bool(msg.media),
                'group': group
            }
            detected_calls.append(call_info)
        
        print("-" * 40)
        
        # Add small delay to avoid overwhelming output
        if i % 10 == 0:
            print(f"\n[INFO] Processed {i} messages so far...")
    
    # Write all detected calls to file
    write_detected_calls_to_file(detected_calls, "COMBINED_DAY_UNIVEST")
    
    print(f"\n{'='*60}")
    print(f"[SUMMARY]")
    print(f"   Total messages processed: {len(all_messages)}")
    print(f"   Daytrade messages: {len(recent_messages)}")
    print(f"   Univest messages: {len(univest_messages)}")
    print(f"   Trading calls detected: {trading_calls_found}")
    print(f"   Success rate: {(trading_calls_found/len(all_messages)*100):.1f}%")
    print(f"   Raw messages saved to: src/test_data/raw_messages/")
    print(f"   Parsing results saved to: src/test_data/parsing_results/")
    print(f"   Images saved to: src/test_data/images/")
    print(f"   Detected calls saved to: detected_trading_calls.txt")
    print("="*60)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())


# client.run_until_disconnected()
