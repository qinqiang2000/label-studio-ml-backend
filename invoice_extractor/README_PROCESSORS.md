# Document Processor System

This system provides a flexible, extensible architecture for processing documents using different AI models or processing strategies.

## Architecture

The system uses the **Strategy Pattern** and **Factory Pattern** to allow easy switching between different document processing implementations:

- `DocumentProcessor` (Abstract Base Class): Defines the interface for all processors
- `GeminiProcessor`: Implementation using Google's Gemini AI model
- `MockProcessor`: Mock implementation for testing
- `DocumentProcessorFactory`: Factory for creating processor instances

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

## Available Processors

### GeminiProcessor
- **Type**: `gemini`
- **Description**: Uses Google's Gemini AI model for document processing
- **Configuration**: 
  - `GEMINI_MODEL`: Model name (optional)
  - `API_KEY`: Google AI API key (required)

### MockProcessor
- **Type**: `mock`
- **Description**: Returns predefined mock data for testing
- **Configuration**: None required

## Usage Examples

### Basic Usage
```python
from invoice_extractor.model import DocumentProcessorFactory

# Create a processor
processor = DocumentProcessorFactory.create_processor('gemini')

# Process a document
result = processor.process_document('/path/to/document.pdf', 'Extract invoice data')
```

### With Configuration
```python
# Create Gemini processor with specific model
processor = DocumentProcessorFactory.create_processor(
    'gemini', 
    model_name='gemini-2.5-flash-preview-05-20'
)
```

### List Available Processors
```python
available = DocumentProcessorFactory.get_available_processors()
print(f"Available processors: {available}")
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