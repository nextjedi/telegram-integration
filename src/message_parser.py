"""
Enhanced Message Parser for Trading Calls
Supports both text and image-based trading call detection and parsing
"""

import re
import datetime
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument


class TradingCallParser:
    """
    Enhanced parser for detecting and extracting trading call information
    from Telegram messages (both text and image-based)
    """
    
    def __init__(self):
        # Expanded instrument list
        self.instruments = [
            # Major Indices
            'BANKNIFTY', 'NIFTY', 'SENSEX', 'FINNIFTY',
            # Individual Stocks
            'IDEA', 'HAL', 'DIXON', 'TATAELXI', 'MOHASIS', 'MCX',
            'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
            'SBIN', 'BHARTIARTL', 'ITC', 'HINDUNILVR', 'KOTAKBANK',
            'ADANIENT', 'TATAMOTORS', 'MARUTI', 'BAJFINANCE', 'LT'
        ]
        
        # Spam/promotional keywords to filter out
        self.spam_indicators = [
            'OFFER', 'LIFETIME', 'JOIN', 'PREMIUM', 'COURSE',
            'QUERY', 'CONTACT', 'HTTPS://', 'HTTP://', '@',
            'SUBSCRIBE', 'MEMBER', 'PAYMENT', 'DISCOUNT'
        ]
        
        # Image-specific promotional/spam indicators
        self.image_spam_indicators = [
            'ZERO TO HERO', 'PROFIT', 'TIMES', 'JACKPOT', 'SURESHOT',
            'MAHA', 'HIGH OF', '🔥', '💎', '🚀', 'HERO', 'BIG',
            'WAIT FOR TRIGGER', 'BOOK PROFIT', 'RETURN', 'DURATION',
            'ENTRY DATE', 'EXIT DATE', 'ENTRY PRICE', 'EXIT PRICE',
            'TAP TO SEE', 'STOCK DETAILS', 'NEW SHORT TERM', 'RECOMMENDATION'
        ]
    
    def is_trading_call(self, message_obj):
        """
        Main method to determine if a message contains a trading call
        Returns: (is_call, parsed_data, call_type)
        """
        try:
            # Check if message has media (image)
            if self._has_image_media(message_obj):
                return self._analyze_image_call(message_obj)
            
            # If text message, analyze text content
            if message_obj.message:
                return self._analyze_text_call(message_obj.message, message_obj)
            
            return False, None, None
            
        except Exception as e:
            print(f"Error parsing message: {e}")
            return False, None, None
    
    def _has_image_media(self, message_obj):
        """Check if message contains image media"""
        if not message_obj.media:
            return False
            
        if isinstance(message_obj.media, MessageMediaPhoto):
            return True
            
        if isinstance(message_obj.media, MessageMediaDocument):
            if hasattr(message_obj.media.document, 'mime_type'):
                mime_type = message_obj.media.document.mime_type
                return mime_type and 'image' in mime_type
        
        return False
    
    def _is_image_spam(self, caption):
        """Check if image caption contains promotional/spam content"""
        if not caption:
            return False
            
        caption_upper = caption.upper()
        
        # Check for image-specific spam indicators
        spam_count = sum(1 for indicator in self.image_spam_indicators if indicator in caption_upper)
        
        # If multiple spam indicators found, it's likely promotional
        if spam_count >= 2:
            return True
            
        # Check for specific promotional patterns
        promotional_patterns = [
            r'ZERO.*HERO',
            r'PROFIT.*\d+.*TIMES',
            r'MAHA.*JACKPOT',
            r'SURESHOT.*CALL',
            r'HIGH OF \d+',
            r'BOOK PROFIT.*:',
            r'RETURN.*\d+%',
            r'DURATION.*MINUTES?',
            r'ENTRY.*DATE.*EXIT.*DATE',
            r'TAP TO SEE'
        ]
        
        for pattern in promotional_patterns:
            if re.search(pattern, caption_upper):
                return True
        
        return False
    
    def _analyze_image_call(self, message_obj):
        """Analyze image-based trading calls with improved spam filtering"""
        caption = message_obj.message if message_obj.message else ""
        
        # Check if image caption is promotional/spam
        if self._is_image_spam(caption):
            return False, None, None
        
        parsed_data = {
            'call_type': 'IMAGE',
            'confidence': 40,  # Start with low confidence for images
            'has_media': True,
            'caption': caption,
            'timestamp': message_obj.date,
            'message_id': message_obj.id,
            'requires_ocr': True
        }
        
        # If caption exists, try to extract info from it
        if caption:
            text_result = self._analyze_text_call(caption, message_obj)
            if text_result[0]:  # If text analysis found patterns
                parsed_data.update(text_result[1])
                parsed_data['confidence'] = min(85, text_result[1].get('confidence', 40) + 10)
                parsed_data['requires_ocr'] = False
            else:
                # No trading data found in caption - likely not a valid call
                return False, None, None
        else:
            # No caption - requires OCR but start with very low confidence
            parsed_data['confidence'] = 30
        
        return True, parsed_data, 'IMAGE_CALL'
    
    def _analyze_text_call(self, message_text, message_obj):
        """Enhanced text analysis with comprehensive pattern matching"""
        if not message_text:
            return False, None, None
            
        msg = message_text.upper().strip()
        
        # Step 1: Filter out promotional/spam messages
        if self._is_spam_message(msg):
            return False, None, None
        
        # Step 2: Check for option type indicators
        option_type = self._extract_option_type(msg)
        if not option_type:
            return False, None, None
        
        # Step 3: Extract instrument name
        instrument = self._extract_instrument(msg)
        
        # Step 4: Extract strike price
        strike_price = self._extract_strike_price(msg, option_type)
        
        # Step 5: Extract entry conditions and trigger price
        trigger_price = self._extract_trigger_price(msg)
        
        # Step 6: Extract stop loss and target
        stop_loss = self._extract_stop_loss(msg)
        target = self._extract_target(msg)
        
        # Step 7: Calculate confidence score
        confidence = self._calculate_confidence(msg, instrument, strike_price, 
                                               trigger_price, stop_loss, target)
        
        # Step 8: Validate as trading call
        is_valid_call = confidence >= 40
        
        if is_valid_call:
            parsed_data = {
                'call_type': 'TEXT',
                'instrument': instrument,
                'strike': strike_price,
                'option_type': option_type,
                'trigger_price': trigger_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': confidence,
                'raw_message': message_text,
                'has_media': False,
                'timestamp': message_obj.date,
                'message_id': message_obj.id
            }
            return True, parsed_data, 'TEXT_CALL'
        
        return False, None, None
    
    def _is_spam_message(self, msg):
        """Check if message is promotional/spam"""
        for indicator in self.spam_indicators:
            if indicator in msg:
                return True
        
        # Check for profit booking messages
        if 'PROFIT' in msg and any(x in msg for x in ['KARA DIYA', 'PARTY KARO']):
            return True
        
        # Check for simple price updates (just numbers with emojis)
        if re.match(r'^\d+[🔥💥🎉]+$', msg.strip()):
            return True
            
        return False
    
    def _extract_option_type(self, msg):
        """Extract option type (CE/PE) using word boundaries to prevent CE/PE confusion"""
        # Use word boundaries and explicit patterns to avoid substring matching issues
        # Check for PE first to avoid CE being found in PE
        if re.search(r'\bPE\b', msg) or re.search(r'\bPUT\b', msg):
            return 'PE'
        elif re.search(r'\bCE\b', msg) or re.search(r'\bCALL\b', msg):
            return 'CE'
        return None
    
    def _extract_instrument(self, msg):
        """Extract instrument name from message"""
        for instrument in self.instruments:
            if instrument in msg:
                return instrument
        return None
    
    def _extract_strike_price(self, msg, option_type):
        """Extract strike price using multiple patterns with word boundaries"""
        # First try to find instrument + strike + option pattern with word boundaries
        for instrument in self.instruments:
            pattern = rf'{instrument}\s+(\d{{1,6}})\s*(?:\bCE\b|\bPE\b|\bCALL\b|\bPUT\b)'
            match = re.search(pattern, msg)
            if match:
                return match.group(1)
        
        patterns = [
            # Pattern 1: Number directly before option type (CE/PE/CALL/PUT) with word boundaries
            r'(\d{1,6})\s*(?:\bCE\b|\bPE\b|\bCALL\b|\bPUT\b)',
            # Pattern 2: Option type followed by number with word boundaries  
            r'(?:\bCE\b|\bPE\b|\bCALL\b|\bPUT\b)\s+(\d{1,6})',
            # Pattern 3: Any 4-6 digit number that's likely a strike
            r'\b(\d{4,6})\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, msg)
            if matches:
                # Return the first reasonable strike price
                for match in matches:
                    strike = int(match)
                    # Basic validation - strike prices should be reasonable
                    if 1 <= strike <= 999999:
                        return str(strike)
        
        return None
    
    def _extract_trigger_price(self, msg):
        """Extract trigger/entry price from message"""
        patterns = [
            r'ABV\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)',  # ABV 50-60 or ABV 2
            r'ABOVE\s+PRICE\s+(\d+(?:\.\d+)?)',           # ABOVE PRICE 340
            r'ABOVE\s+(\d+(?:\.\d+)?)',                   # ABOVE 20
            r'PRICE\s+(\d+(?:\.\d+)?)',                   # PRICE 340
            r'@\s*(\d+(?:\.\d+)?)',                       # @ 50
            r'AT\s+(\d+(?:\.\d+)?)'                       # AT 25
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_stop_loss(self, msg):
        """Extract stop loss from message"""
        patterns = [
            r'SL\s+(\d+(?:\.\d+)?)',
            r'STOPLOSS\s+(\d+(?:\.\d+)?)',
            r'STOP\s+LOSS\s+(\d+(?:\.\d+)?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_target(self, msg):
        """Extract target price from message"""
        patterns = [
            r'TARGET\s+([\d+/\.\+\-]+)',
            r'TGT\s+([\d+/\.\+\-]+)',
            r'TARGET:\s*([\d+/\.\+\-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg)
            if match:
                return match.group(1)
        
        return None
    
    def _calculate_confidence(self, msg, instrument, strike, trigger, stop_loss, target):
        """Calculate confidence score for the trading call with enhanced validation"""
        confidence = 0
        
        # Enhanced validation: Require essential trading parameters for any meaningful confidence
        essential_params = [instrument, strike, trigger]
        essential_count = sum(1 for param in essential_params if param)
        
        # Base confidence based on essential parameters
        if essential_count == 3:  # All essential params present
            confidence += 60
        elif essential_count == 2:  # Two essential params
            confidence += 45
        elif essential_count == 1:  # One essential param
            confidence += 25
        else:  # No essential params - very low confidence
            confidence += 10
        
        # Additional validation factors
        if instrument:
            confidence += 10
        if stop_loss:
            confidence += 8
        if target:
            confidence += 8
        
        # Entry pattern validation
        if any(keyword in msg for keyword in ['ABV', 'ABOVE', 'AT', '@']):
            confidence += 12
        
        # Option type validation
        if any(opt in msg for opt in ['CE', 'PE', 'CALL', 'PUT']):
            confidence += 10
        
        # Special call indicators (but reduce their impact to prevent false positives)
        if 'ZERO HERO' in msg:
            confidence += 15  # Reduced from 20
        if 'SURESHOT' in msg or '100%' in msg:
            confidence += 8   # Reduced from 15
        
        # Negative factors (stronger penalties for incomplete calls)
        if len(msg.strip()) < 15:  # Increased minimum length
            confidence -= 25
        if not any(opt in msg for opt in ['CE', 'PE', 'CALL', 'PUT']):
            confidence -= 35  # Increased penalty
        if essential_count < 2:  # Missing too many essential params
            confidence -= 20
        
        # Ensure high confidence requires complete trading information
        if confidence >= 70 and essential_count < 3:
            confidence = min(69, confidence)  # Cap at medium confidence
        
        return max(0, min(100, confidence))
    
    def calculate_smart_sl_target(self, trigger_price, option_type='PE'):
        """Calculate smart stop loss and target based on price level"""
        if not trigger_price:
            return None, None
            
        try:
            # Handle range prices (e.g., "50-60")
            if '-' in trigger_price:
                trigger = float(trigger_price.split('-')[0])
            else:
                trigger = float(trigger_price)
            
            # Smart stop loss calculation based on price level
            if trigger <= 2:
                sl = max(0.5, trigger * 0.5)  # 50% for very low priced options
            elif trigger <= 10:
                sl = trigger - 1  # 1 point for low priced
            elif trigger <= 50:
                sl = trigger - 5  # 5 points for mid range
            else:
                sl = trigger - (trigger * 0.15)  # 15% for high priced
            
            # Smart target calculation (risk-reward based)
            risk = trigger - sl
            target1 = trigger + (risk * 1.5)  # 1:1.5 RR
            target2 = trigger + (risk * 2.5)  # 1:2.5 RR
            
            return round(sl, 2), f"{round(target1, 2)}/{round(target2, 2)}"
            
        except (ValueError, AttributeError):
            return None, None


def enhanced_message_processor(message_obj):
    """
    Main function to process messages using the enhanced parser
    """
    parser = TradingCallParser()
    is_call, parsed_data, call_type = parser.is_trading_call(message_obj)
    
    if not is_call:
        return None
    
    # Add smart stop loss and target calculation for text calls
    if call_type == 'TEXT_CALL' and parsed_data.get('trigger_price'):
        smart_sl, smart_target = parser.calculate_smart_sl_target(
            parsed_data['trigger_price'], 
            parsed_data.get('option_type', 'PE')
        )
        if smart_sl:
            parsed_data['smart_sl'] = smart_sl
        if smart_target:
            parsed_data['smart_target'] = smart_target
    
    return {
        'type': call_type.lower().replace('_call', ''),
        'data': parsed_data,
        'confidence': parsed_data.get('confidence', 0),
        'timestamp': parsed_data.get('timestamp'),
        'message_id': parsed_data.get('message_id')
    }


# Test function for development
def test_parser():
    """Test function to validate parser with sample messages"""
    
    class MockMessage:
        def __init__(self, text, media=None):
            self.message = text
            self.media = media
            self.date = datetime.datetime.now()
            self.id = 12345
    
    test_messages = [
        "BANKNIFTY 55600 PUT ABOVE 340",
        "SENSEX 81400 PE ABV 50-60",
        "IDEA 9 PE ABV 2",
        "NIFTY 25100 PUT ABOVE 20",
        "KARA DIYA 80,000 PROFIT",  # Should be filtered out
        "120 FIRE",  # Should be filtered out
        "BUY ZERO HERO SENSEX 83000 CE ABV 50-60"
    ]
    
    parser = TradingCallParser()
    
    print("=== TESTING ENHANCED PARSER ===\n")
    
    for i, msg_text in enumerate(test_messages, 1):
        print(f"Test {i}: {msg_text}")
        mock_msg = MockMessage(msg_text)
        
        is_call, data, call_type = parser.is_trading_call(mock_msg)
        
        if is_call:
            print(f"  [OK] Detected: {call_type}")
            print(f"  [CONF] Confidence: {data.get('confidence', 0)}%")
            if call_type == 'TEXT_CALL':
                print(f"  [INST] Instrument: {data.get('instrument', 'N/A')}")
                print(f"  [STRK] Strike: {data.get('strike', 'N/A')}")
                print(f"  [TYPE] Type: {data.get('option_type', 'N/A')}")
                print(f"  [ENTR] Entry: {data.get('trigger_price', 'N/A')}")
                print(f"  [SL] SL: {data.get('smart_sl', 'N/A')}")
                print(f"  [TGT] Target: {data.get('smart_target', 'N/A')}")
        else:
            print(f"  [SKIP] Not a trading call")
        
        print("-" * 50)


if __name__ == "__main__":
    test_parser()