# Document Processors

This directory contains different document processors that can be used for document understanding tasks.

## Available Processors

### 1. GeminiProcessor

Uses Google's Gemini API for document processing.

#### Configuration

The GeminiProcessor handles its own parameter configuration through environment variables:

**Basic Configuration:**
```bash
API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-preview-04-17
```

**Advanced LLM Parameters:**
```bash
# Temperature: Controls randomness (0.0-2.0, default: 0.1)
GEMINI_TEMPERATURE=0.1

# Maximum output tokens
GEMINI_MAX_OUTPUT_TOKENS=8192

# Top P: Nucleus sampling (0.0-1.0)
GEMINI_TOP_P=0.95

# Top K: Top-k sampling (integer)
GEMINI_TOP_K=40

# Random seed for reproducibility
GEMINI_SEED=12345

# Number of response candidates
GEMINI_CANDIDATE_COUNT=1

# Stop sequences (comma-separated)
GEMINI_STOP_SEQUENCES="END,STOP"

# Presence penalty (-2.0 to 2.0)
GEMINI_PRESENCE_PENALTY=0.0

# Frequency penalty (-2.0 to 2.0)
GEMINI_FREQUENCY_PENALTY=0.0

# Response MIME type
GEMINI_RESPONSE_MIME_TYPE=text/plain

# Thinking budget (0 means no thinking)
GEMINI_THINKING_BUDGET=0
```

#### Usage Examples

**Environment Variables:**
```python
# Parameters are automatically loaded from environment variables
processor = GeminiProcessor()
```

**Custom Configuration:**
```python
# Custom parameters override environment variables
custom_config = {
    "temperature": 0.2,
    "max_output_tokens": 4096,
    "top_p": 0.9
}
processor = GeminiProcessor(llm_param_config=custom_config)
```

### 2. MockProcessor

Uses mock data for testing purposes.

#### Configuration
No special configuration needed. Uses predefined mock responses.

## Architecture

Each processor is responsible for:
1. **Parameter Management**: Reading from environment variables and handling custom configurations
2. **API Integration**: Managing the specific API client and authentication
3. **Response Processing**: Converting API responses to the expected format
4. **Error Handling**: Managing processor-specific errors and edge cases

## Adding New Processors

To add a new processor:

1. Create a new file in `processors/` directory
2. Inherit from `DocumentProcessor` base class
3. Implement required methods: `process_document()` and `get_model_version()`
4. Handle your processor's specific parameters in the `__init__` method
5. Register the processor in `factory.py`

Example:
```python
class MyProcessor(DocumentProcessor):
    def __init__(self, **kwargs):
        # Handle your processor's specific parameters here
        self.param1 = os.environ.get('MY_PARAM1', 'default')
        self.param2 = kwargs.get('custom_param', 'default')
    
    def process_document(self, file_path: str, instruction: str) -> str:
        # Your processing logic here
        pass
    
    def get_model_version(self) -> str:
        return "my-processor-v1.0"
```

## Configuration

### Environment Variables

- `DOCUMENT_PROCESSOR`: Specifies which processor to use (`gemini`, `mock`)
- `GEMINI_MODEL`: Specifies which Gemini model to use (default: `gemini-2.5-flash-preview-04-17`)
- `USE_MOCK_DATA`: Set to `true` or `1` to force mock data usage

### Examples

```bash
# Use Gemini processor with default model
export DOCUMENT_PROCESSOR=gemini

# Use Gemini processor with specific model
export DOCUMENT_PROCESSOR=gemini
export GEMINI_MODEL=gemini-2.5-flash-preview-05-20

# Use mock processor for testing
export DOCUMENT_PROCESSOR=mock

# Force mock data regardless of processor
export USE_MOCK_DATA=true
```

## Adding Custom Processors

### Step 1: Create Your Processor Class

```python
from invoice_extractor.model import DocumentProcessor
import logging

logger = logging.getLogger(__name__)

class CustomProcessor(DocumentProcessor):
    """Custom document processor implementation"""
    
    def __init__(self, api_key: str, model_name: str = "custom-model-v1"):
        self.api_key = api_key
        self.model_name = model_name
        # Initialize your custom client/model here
    
    def process_document(self, file_path: str, instruction: str) -> str:
        """Process document using your custom implementation"""
        logger.info(f'Processing document with custom processor: {file_path}')
        
        # Your custom processing logic here
        # This should return a JSON string
        result = {
            "docType": "invoice",
            "totalAmount": 1000.0,
            "currency": "USD"
            # ... other fields
        }
        
        return json.dumps([result])
    
    def get_model_version(self) -> str:
        return f"custom-processor-{self.model_name}"
```

### Step 2: Register Your Processor

```python
from invoice_extractor.model import DocumentProcessorFactory

# Register your custom processor
DocumentProcessorFactory.register_processor('custom', CustomProcessor)
```

### Step 3: Use Your Processor

```bash
export DOCUMENT_PROCESSOR=custom
```

## Benefits

1. **Flexibility**: Easy to switch between different AI models or processing strategies
2. **Extensibility**: Simple to add new processors without modifying existing code
3. **Testability**: Mock processor allows for testing without API calls
4. **Configuration**: Environment-based configuration for different deployment scenarios
5. **Maintainability**: Clean separation of concerns between different processing strategies

## Migration from Old Code

The old hardcoded Gemini implementation has been replaced with this flexible system. The behavior remains the same by default, but now you have the option to:

- Switch to different Gemini models
- Add custom processors
- Use mock data for testing
- Easily extend with new AI providers

No changes are required to existing usage - the system will default to Gemini processor if no configuration is provided. 