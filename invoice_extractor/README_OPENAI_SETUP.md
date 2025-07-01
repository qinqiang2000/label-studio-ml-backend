# OpenAI GPT-4.1 Processor Setup Guide

## Overview

This guide explains how to set up and use the OpenAI GPT-4.1 processor for document extraction in the label-studio-ml-backend.

## Prerequisites

1. **OpenAI API Account**: You need a valid OpenAI API account with access to GPT-4.1
2. **API Key**: Generate an API key from [OpenAI Platform](https://platform.openai.com/api-keys)
3. **Python Dependencies**: Install the required OpenAI package

## Installation

### 1. Install Dependencies

```bash
cd /Users/qinqiang02/colab/codespace/ai/label-studio-ml-backend/invoice_extractor
pip install -r requirements.txt
```

The `requirements.txt` now includes `openai>=1.0.0`.

### 2. Set Environment Variables

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

Or add it to your `.env` file:

```bash
echo "OPENAI_API_KEY=your-openai-api-key-here" >> .env
```

## Available OpenAI Models

The processor supports the following OpenAI models:

- **gpt-4.1**: Latest GPT-4.1 model (default)
- **gpt-4o**: GPT-4o with vision and text capabilities

## Testing

### 1. Test OpenAI Model Availability

First, check if OpenAI models are available:

```bash
cd tests
python test_versions_api.py
```

Look for OpenAI models in the response:

```json
{
  "processor_type": "openai",
  "model_name": "gpt-4.1",
  "version_string": "openai|gpt-4.1",
  "description": "OpenAI GPT-4.1 (Latest)",
  "is_default": false
}
```

### 2. Test OpenAI Prediction

Test OpenAI model with a document:

```bash
cd tests
python test_openai_model.py
```

### 3. Compare All Models

Test all available models (Gemini, OpenAI, Mock):

```bash
cd tests
python test_predict_with_model_version.py
```

## Usage Examples

### 1. Using curl

```bash
curl -X POST http://127.0.0.1:9090/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [{
      "id": 1362,
      "data": {
        "pdf": "<embed src=\"/data/local-files/?d=28/495d02f7.pdf\" width=\"100%\" height=\"811px\"/>",
        "filename": "test.pdf",
        "invoices_json": ""
      }
    }],
    "label_config": "...",
    "params": {
      "model_version": "openai|gpt-4.1"
    }
  }'
```

### 2. Using Python

```python
import requests

payload = {
    "tasks": [...],
    "label_config": "...",
    "params": {
        "model_version": "openai|gpt-4.1",
        "runtime_config": {
            "temperature": 0.1,
            "max_output_tokens": 30000
        }
    }
}

response = requests.post(
    "http://127.0.0.1:9090/predict",
    json=payload
)
```

## Runtime Configuration

The OpenAI processor supports the following runtime configuration options:

- **temperature**: Sampling temperature (0.0-2.0, default: 0)
- **max_output_tokens**: Maximum output tokens (default: 30000 for images, 300000 for documents)

Example:

```json
{
  "params": {
    "model_version": "openai|gpt-4.1",
    "runtime_config": {
      "temperature": 0.1,
      "max_output_tokens": 50000
    }
  }
}
```

## File Support

The OpenAI processor supports:

### Images (processed via OpenAI Vision)
- `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`

### Documents (processed via OpenAI File API)
- `.pdf`, `.docx`, `.doc`, `.txt`, `.md`

## Performance Notes

1. **Cost**: OpenAI models are typically more expensive than other options
2. **Speed**: Response times may vary based on document size and complexity
3. **Quotas**: Be aware of your OpenAI API usage limits and quotas
4. **File Cleanup**: The processor automatically uploads and deletes files from OpenAI

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   Error: OPENAI_API_KEY environment variable is required
   ```
   Solution: Set the `OPENAI_API_KEY` environment variable

2. **Import Error**
   ```
   Error: OpenAI package is not available
   ```
   Solution: Install OpenAI package: `pip install openai>=1.0.0`

3. **API Quota Exceeded**
   ```
   Error: You exceeded your current quota
   ```
   Solution: Check your OpenAI account billing and usage limits

4. **Model Not Available**
   ```
   Error: The model 'gpt-4.1' does not exist
   ```
   Solution: Verify model availability in your OpenAI account

### Debug Mode

Enable debug logging to see detailed request/response information:

```bash
export LOG_LEVEL=DEBUG
python _wsgi.py
```

## Integration with Label Studio

Once the ML Backend is running with OpenAI support, the model will appear in Label Studio's "Retrieve Predictions" action dialog:

1. Select tasks in Label Studio Data Manager
2. Choose "Retrieve Predictions" action  
3. Select "OpenAI GPT-4.1 (Latest)" from the model version dropdown
4. Execute the action

The OpenAI processor will be used for document extraction, and results will be displayed in Label Studio.

## Cost Considerations

- OpenAI GPT-4.1 pricing varies by token usage
- Monitor your usage through the OpenAI dashboard
- Consider using Gemini models for cost-sensitive applications
- Use the Mock processor for testing and development