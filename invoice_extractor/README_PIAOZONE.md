# PiaoZone Processor Documentation

## Overview

The PiaoZone processor provides integration with PiaoZone AI API for document understanding and processing. It supports various AI models (currently Gemini models) through the PiaoZone API gateway.

## Features

- Dynamic token acquisition and management
- Automatic token refresh
- Support for multiple Gemini models
- Configurable model parameters
- Schema validation and normalization
- Multiple file format support (PDF, PNG, JPG/JPEG)

## Configuration

### Token Management

The PiaoZone processor supports two authentication methods:

#### 1. Static Token (Backward Compatible)

Set a static access token in environment variables:

```bash
export PIAOZONE_ACCESS_TOKEN="your_static_access_token"
```

#### 2. Dynamic Token (Recommended)

Configure client credentials for automatic token acquisition:

```bash
export PIAOZONE_CLIENT_ID="Q3V07mngUYcDOGeELsIS"
export PIAOZONE_CLIENT_SECRET="163e7765d14c4601a26931493ca57634"
export PIAOZONE_TOKEN_URL="https://api-sit.piaozone.com/base/oauth/token"
export PIAOZONE_TOKEN_DURATION_HOURS="24"  # Optional, defaults to 24 hours
```

The dynamic token method will:
- Automatically fetch a new token when needed
- Cache the token for the specified duration
- Refresh the token 5 minutes before expiration
- Handle token failures gracefully

### API Configuration

```bash
export PIAOZONE_API_URL="https://api-sit.piaozone.com/ai/knowledge/v1/chat/completions"
export PIAOZONE_MODEL="gemini-2.5-flash-preview-04-17"
```

### Model Parameters

```bash
export PIAOZONE_TEMPERATURE="0.1"                # Temperature (0.0-2.0)
export PIAOZONE_MAX_OUTPUT_TOKENS="8192"         # Maximum output tokens
export PIAOZONE_TOP_P="0.95"                     # Top-p sampling
export PIAOZONE_TOP_K="40"                       # Top-k sampling
export PIAOZONE_SEED="12345"                     # Random seed for reproducibility
export PIAOZONE_RESPONSE_MIME_TYPE="application/json"  # Response format
export PIAOZONE_THINKING_BUDGET="0"              # Deep thinking budget
```

## Usage

### Basic Usage

```python
from processors.piaozone import PiaoZoneProcessor

# Create processor instance
processor = PiaoZoneProcessor()

# Process a document
result = processor.process_document(
    "path/to/document.pdf",
    "Extract invoice information including invoice number, date, and total amount"
)

print(result)
```

### With Runtime Configuration

```python
# Override default configuration at runtime
runtime_config = {
    "temperature": 0.2,
    "response_mime_type": "application/json",
    "response_schema": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total_amount": {"type": "number"},
            "date": {"type": "string"}
        },
        "required": ["invoice_number", "total_amount", "date"]
    }
}

result = processor.process_document(
    "invoice.pdf",
    "Extract invoice data",
    runtime_config
)
```

### Using with Label Studio ML Backend

Set the model version in Label Studio to use PiaoZone processor:

```
piaozone|gemini-2.5-flash-preview-04-17
```

## Token Acquisition Flow

When using dynamic token management:

1. The processor checks for a static token first (backward compatibility)
2. If no static token, it checks for a cached valid token
3. If no valid cached token, it fetches a new token using:
   - Current timestamp
   - Client ID and Secret
   - MD5 signature: `MD5(client_id + client_secret + timestamp)`
4. The new token is cached with an expiration time
5. Tokens are automatically refreshed 5 minutes before expiration

## Testing

### Run Unit Tests

```bash
# Test token manager
python test_piaozone_token.py

# Test processor functionality
python test_piaozone.py
```

### Test with Real Document

```bash
export PIAOZONE_CLIENT_ID="your_client_id"
export PIAOZONE_CLIENT_SECRET="your_client_secret"
export PIAOZONE_TEST_DOCUMENT="/path/to/test/document.pdf"

python test_piaozone_token.py
```

## Troubleshooting

### Common Issues

1. **Token Acquisition Failed**
   - Verify `PIAOZONE_CLIENT_ID` and `PIAOZONE_CLIENT_SECRET` are correct
   - Check network connectivity to PiaoZone API
   - Verify the token URL is accessible

2. **API Request Failed**
   - Check if the token is valid
   - Verify API URL is correct
   - Check file size limits (if any)
   - Review API response for specific error messages

3. **Schema Validation Errors**
   - PiaoZone requires uppercase type names in schemas
   - The processor automatically normalizes schemas
   - Check that required fields match the actual response

### Debug Mode

Enable debug logging to see detailed request/response information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Notes

- Never commit credentials to version control
- Use environment variables or secure vaults for production
- Rotate client secrets regularly
- Monitor token usage and API access logs