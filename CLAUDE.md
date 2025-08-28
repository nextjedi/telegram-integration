# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A sophisticated Telegram-based trading signal monitoring system that detects options trading calls from specific channels and forwards them to an API endpoint for automated trading. The system specializes in BANKNIFTY and FINNIFTY options with advanced pattern recognition and confidence scoring.

## High-Level Architecture

### Message Processing Pipeline
```
Telegram Channels → Telethon Client → Enhanced Parser → Confidence Filter → API Forward → User Notification
```

### Core Components

**Trading Signal Detection Engine**
- `src/groupmessage.py`: Multi-channel monitor with enhanced processing - main entry point
- `src/message_parser.py`: Advanced `TradingCallParser` with confidence scoring (40-100% scale)
- `src/telegram-message.py`: Legacy single-channel implementation

**Signal Processing Flow**
1. Messages received from monitored channels (daytrade: -1001752927494, btst: -1001552501322, univest: -1001983880498)
2. `enhanced_message_processor()` analyzes both text and image-based calls
3. Confidence thresholds filter signals (High ≥70%, Medium 50-69%, Low <50%)
4. High confidence calls trigger API forwarding to trading endpoint
5. Smart stop loss/target calculation based on price levels

## Commands

### Development Commands
```bash
# Install dependencies
pip install -r src/requirements.txt

# Run the main monitoring script
py src/groupmessage.py

# Test the message parser independently
py src/message_parser.py

# Linting
flake8 src/
find src/ -type f -name "*.py" | xargs pylint

# Run tests (when implemented)
pytest
pytest --cov  # with coverage
```

## Message Parsing Patterns

### Recognized Trading Call Formats
- Standard: `BANKNIFTY 55600 PUT ABOVE 340`
- Range: `SENSEX 82100 PE ABV 470-520`
- Stock: `HAL 4500 PUT Above price 60`
- Special: `ZERO HERO` prefix adds +20% confidence

### Parser Intelligence
- **Instruments**: BANKNIFTY, NIFTY, FINNIFTY, SENSEX + 15 major stocks
- **Option Types**: CE/PE, CALL/PUT detection
- **Entry Patterns**: ABOVE, ABV, @, AT, PRICE keywords
- **Spam Filtering**: Promotional keywords, profit booking messages, simple price updates
- **Image Support**: Detects trading images with 85% base confidence

### Confidence Scoring Algorithm
- Base: instrument + strike + trigger = 50%
- Bonuses: +15% instrument, +10% SL, +10% target, +20% "ZERO HERO"
- Minimum threshold: 40% to be considered valid

## API Integration

### Trading API Format
```python
{
    "instrument": {"name": "BANKNIFTY", "strike": "55600", "instrumentType": "PE"},
    "price": trigger_price,
    "stopLoss": calculated_sl,
    "target": calculated_target,
    "confidence": confidence_score,
    "type": "DAY/BTST",
    "parser_version": "enhanced_v1"
}
```

### Endpoint Configuration
- Production: `https://tip-based-trading.azurewebsites.net/tip`
- Currently commented out for testing mode

## Critical Security Notes

⚠️ **Hardcoded Credentials**: API keys, phone numbers, and channel IDs are hardcoded in source
⚠️ **Session Files**: `session_name.session` contains Telegram auth - do not commit
⚠️ **Move to Environment Variables**: All sensitive data should use environment variables

## Testing Approach

When testing trading calls:
1. Check `detected_trading_calls.txt` for recent detection results
2. Use `handleMessages()` function for testing individual messages
3. API calls are commented out in `groupmessage.py` (around lines 156-181)
4. Monitor console output for confidence scores and detection details

## Development Status

- Enhanced parser recently implemented with smart SL/target calculation
- API forwarding disabled for testing (uncomment lines 160-181 in groupmessage.py)
- Multiple analysis scripts available for debugging patterns
- Active feature branch: `feature/telegram`