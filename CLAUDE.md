# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Label Studio ML backend repository focused on document processing and analysis. The project's core functionality is:

- **Invoice Extractor (Core)**: Located in `invoice_extractor/` - the main implementation for document processing using various AI models (Gemini, OpenAI)
- **Core ML Backend Framework**: Located in `label_studio_ml/` - provides the base classes and infrastructure (peripheral)
- **Examples**: Located in `label_studio_ml/examples/` - various pre-built ML backends for reference (can be ignored)

## Development Commands

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Install invoice extractor dependencies
pip install -r invoice_extractor/requirements.txt
```

### Running & Testing
```bash
# Run tests
make test
# or
pytest tests

# Start the main invoice extractor backend
label-studio-ml start ./invoice_extractor --host 0.0.0.0 --port 9091 --debug

# Create a new ML backend (if needed)
label-studio-ml create my_backend_name
```

### Docker Commands
```bash
# Build and run with Docker (from invoice_extractor directory)
cd invoice_extractor
docker-compose up

# Force rebuild without cache
docker compose build --no-cache
```

## Architecture Overview

### Core Framework (Peripheral)

1. **LabelStudioMLBase** (`label_studio_ml/model.py`): Abstract base class that all ML backends inherit from
   - Provides `predict()` method for inference
   - Provides `fit()` method for training/updating models
   - Handles caching, label configuration, and Label Studio integration
   - Key properties: `model_version`, `label_config`, `parsed_label_config`

2. **Server Infrastructure** (`label_studio_ml/server.py`): 
   - Command-line interface for creating and starting ML backends
   - Auto-discovery of ML backend classes

3. **Response System** (`label_studio_ml/response.py`):
   - `ModelResponse` class for handling predictions and errors
   - Unified error handling across different processors

### Invoice Extractor Architecture (Main Focus)

The invoice extractor is the core implementation with advanced patterns:

1. **Processor Factory Pattern** (`invoice_extractor/processors/factory.py`):
   - Creates different document processors (Gemini, OpenAI, Mock)
   - Handles processor switching at runtime
   - Manages model version strings in format "processor_type|model_name"

2. **Document Processor Interface** (`invoice_extractor/processors/base.py`):
   - Abstract base class for all document processors
   - Defines `process_document()` and `get_model_version()` methods

3. **Configuration Management** (`invoice_extractor/config/`):
   - Runtime configuration for AI models (temperature, response_schema, etc.)
   - Model version validation and switching
   - YAML-based configuration files

4. **Analyzer Components** (`invoice_extractor/analyzers/`):
   - Specialized analyzers for different document types (Excel, etc.)
   - Delegates processing to appropriate processors

### Key Patterns

1. **Caching System**: Uses SQLite-based caching for model state persistence
2. **Environment Configuration**: Extensive use of environment variables for configuration
3. **Proxy Support**: Built-in HTTP/HTTPS proxy configuration for restricted networks
4. **Error Handling**: Comprehensive error categorization and reporting
5. **Model Versioning**: Support for switching between different AI models at runtime

## Working with the Codebase

### Primary Development (Invoice Extractor)

Focus on the `invoice_extractor/` directory for main development:

1. **Main Model**: `invoice_extractor/model.py` - contains the `NewModel` class
2. **Document Processors**: `invoice_extractor/processors/` - add new AI model integrations
3. **Configuration**: `invoice_extractor/config/` - model and runtime configurations
4. **Testing**: `invoice_extractor/tests/` - test files for the main implementation

### Adding New Document Processors

1. Create processor class inheriting from `DocumentProcessor` in `invoice_extractor/processors/`
2. Register in `invoice_extractor/processors/factory.py`
3. Add configuration in `invoice_extractor/config/models.yaml`
4. Update version parsing logic in `invoice_extractor/model.py`

### Environment Variables

Key environment variables used across the project:
- `LABEL_STUDIO_URL`: Label Studio instance URL
- `LABEL_STUDIO_API_KEY`: API key for Label Studio access
- `DOCUMENT_PROCESSOR`: Processor type (gemini, openai, mock)
- `API_KEY`: API key for AI services
- `USING_PROXY`: Enable proxy configuration
- `MODEL_DIR`: Directory for model storage and caching

### Testing

- Invoice extractor tests in `invoice_extractor/tests/` directory
- Core framework tests in `tests/` directory
- Use `pytest` for running tests
- Mock processors available for testing without API calls

## File Structure Notes

- `/invoice_extractor/`: **Main project focus** - core document processing implementation
- `/label_studio_ml/`: Framework infrastructure (peripheral)
- `/label_studio_ml/examples/`: Reference examples (can be ignored)
- `/tests/`: Unit tests for core framework

## Development Tips

1. **Primary Focus**: Work mainly in `invoice_extractor/` directory - this is the core implementation
2. **Starting the Server**: Use `label-studio-ml start ./invoice_extractor --host 0.0.0.0 --port 9091 --debug`
3. **Model Version Management**: Use format "processor_type|model_name" for runtime model switching
4. **Error Handling**: Always use `ModelResponse` for consistent error reporting
5. **Configuration**: Check both environment variables and config files for settings
6. **Testing**: Use mock processors to test without external API dependencies
7. **Examples**: The `label_studio_ml/examples/` directory can be ignored - it's just reference material