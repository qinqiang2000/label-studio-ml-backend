# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Label Studio ML backend repository focused on document processing and analysis. The project's core functionality is:

- **Invoice Extractor (Core)**: Located in `invoice_extractor/` - the **ONLY actively maintained** implementation for document processing using various AI models (Gemini, OpenAI, Piaozone)
- **Core ML Backend Framework**: Located in `label_studio_ml/` - provides the base classes and infrastructure (modified from upstream to add `/analyze` endpoint)
- **Examples**: Located in `label_studio_ml/examples/` - legacy reference examples (NOT maintained, can be ignored)

## Deployment & Operations

### Production Deployment (Primary Method)
```bash
# Deploy to production server (129.226.88.226:9091)
./deploy.sh

# The script automatically:
# - Commits and pushes code changes
# - Stops old containers
# - Pulls latest code on remote server
# - Builds Docker image from project root (includes modified label_studio_ml)
# - Starts container with proper logging
# - Runs health checks on all endpoints
```

**Important**: Always use `./deploy.sh` for deployment. Manual docker commands are NOT recommended as they may miss critical configurations.

### Monitoring & Debugging
```bash
# View container logs (file-based, persisted)
./logs.sh -f              # Real-time log following
./logs.sh -t 100          # Show last 100 lines
./logs.sh -e              # Show only errors
./logs.sh -g 'pattern'    # Search for pattern
./logs.sh --save          # Save logs to local file

# Logs are written to: /var/log/invoice-extractor.log (on remote server)
```

### Local Development (Testing Only)
```bash
# Install dependencies for local testing
pip install -r invoice_extractor/requirements.txt

# Run tests
pytest invoice_extractor/tests/

# Local server (for development only, NOT for production)
cd invoice_extractor
python start_with_custom_endpoints.py --port 9090 --debug
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

The invoice extractor is the **ONLY actively maintained** implementation with advanced patterns:

1. **Processor Factory Pattern** (`invoice_extractor/processors/factory.py`):
   - Creates different document processors: **Gemini** (primary), **OpenAI**, **Piaozone** (invoice OCR), **Mock** (testing)
   - Handles processor switching at runtime via `model_version` parameter
   - Model version format: `"processor_type|model_name"` (e.g., `"gemini|gemini-2.5-flash"`)

2. **Document Processor Interface** (`invoice_extractor/processors/base.py`):
   - Abstract base class for all document processors
   - Key methods: `process_document()`, `get_model_version()`
   - Supports runtime configuration (temperature, response_schema, etc.)

3. **Configuration Management** (`invoice_extractor/config/`):
   - `models.yaml`: Model definitions and defaults
   - `manager.py`: Runtime config validation, IP whitelist, model switching
   - Environment-based configuration for API keys

4. **Analyzer Components** (`invoice_extractor/analyzers/`):
   - **ExcelAnalyzer**: Gemini-powered Excel file analysis (converts to CSV, uploads to Gemini)
   - Delegates processing to configured processors

### Key Patterns

1. **Caching System**: Uses SQLite-based caching for model state persistence
2. **Environment Configuration**: Extensive use of environment variables for configuration
3. **Proxy Support**: Built-in HTTP/HTTPS proxy configuration for restricted networks
4. **Error Handling**: Comprehensive error categorization and reporting
5. **Model Versioning**: Support for switching between different AI models at runtime

## API Endpoints

The service exposes the following endpoints (deployed at `http://129.226.88.226:9091`):

### Standard Endpoints
- `POST /predict` - Process documents for Label Studio annotations (main endpoint)
- `POST /analyze` - Analyze Excel files with Gemini (returns markdown report)
- `POST /setup` - Initialize model configuration
- `POST /webhook` - Handle Label Studio webhook events
- `GET /health` - Basic health check
- `GET /metrics` - System metrics

### Custom Endpoints (added in `custom_api.py`)
- `GET /versions` - List all available model versions
- `GET /model/info` - Get current model information
- `GET /health/detailed` - Detailed health status
- `GET /test` - Test logging and git info

See `invoice_extractor/README_ANALYZE.md` for `/analyze` endpoint details.

## Working with the Codebase

### Primary Development (Invoice Extractor ONLY)

**Focus exclusively on `invoice_extractor/` directory** - this is the only maintained code:

1. **Main Model**: `invoice_extractor/model.py` - `NewModel` class (inherits from `LabelStudioMLBase`)
2. **Document Processors**: `invoice_extractor/processors/` - AI model integrations
   - `gemini.py` - Google Gemini processor (primary)
   - `openai.py` - OpenAI processor
   - `piaozone.py` - Piaozone invoice OCR
   - `mock.py` - Mock processor for testing
3. **Configuration**: `invoice_extractor/config/` - YAML configs and manager
4. **Analyzers**: `invoice_extractor/analyzers/` - Excel analysis with Gemini
5. **API Extensions**: `invoice_extractor/custom_api.py` - Custom endpoint definitions

### Adding New Document Processors

1. Create processor class inheriting from `DocumentProcessor` in `invoice_extractor/processors/`
2. Implement `process_document()` and `get_model_version()` methods
3. Register in `invoice_extractor/processors/factory.py` (`PROCESSORS` dict and `get_available_processors()`)
4. Add model configuration in `invoice_extractor/config/models.yaml`
5. Deploy with `./deploy.sh` to update production

### Environment Variables (configured in `invoice_extractor/.env`)

**Required**:
- `API_KEY` - Gemini API key (primary)
- `LABEL_STUDIO_URL` - Label Studio instance URL
- `LABEL_STUDIO_API_KEY` - API key for Label Studio access

**Optional**:
- `DOCUMENT_PROCESSOR` - Processor type: `gemini`|`openai`|`piaozone`|`mock` (default: gemini)
- `GEMINI_MODEL` - Gemini model name (default: gemini-2.5-flash)
- `ANALYSIS_MODEL` - Model for Excel analysis (default: gemini-2.5-flash)
- `USING_PROXY` - Enable HTTP proxy (TRUE/FALSE)
- `MODEL_DIR` - Model cache directory (default: current dir)
- `LOG_LEVEL` - Logging level: DEBUG|INFO|WARNING|ERROR (default: INFO)

### Testing

```bash
# Run tests locally
pytest invoice_extractor/tests/

# Specific test files
pytest invoice_extractor/tests/test_api.py
pytest invoice_extractor/tests/test_processor_integration.py

# Mock processor available for testing without API calls
DOCUMENT_PROCESSOR=mock pytest invoice_extractor/tests/
```

## File Structure Notes

```
label-studio-ml-backend/
├── invoice_extractor/          # ⭐ ONLY actively maintained code
│   ├── model.py                # Main ML model (NewModel class)
│   ├── processors/             # AI model processors (Gemini, OpenAI, Piaozone, Mock)
│   ├── analyzers/              # Document analyzers (Excel, etc.)
│   ├── config/                 # Configuration management
│   ├── custom_api.py           # Custom endpoint definitions
│   ├── _wsgi.py                # WSGI entry point with custom endpoints
│   ├── start_with_custom_endpoints.py  # Standalone server script
│   ├── tests/                  # Test files
│   ├── .env                    # Environment variables (not in git)
│   ├── Dockerfile              # Container definition
│   └── README_ANALYZE.md       # /analyze endpoint documentation
├── label_studio_ml/            # Modified framework (adds /analyze endpoint)
│   ├── api.py                  # API endpoints (modified to add /analyze)
│   ├── model.py                # Base class (LabelStudioMLBase)
│   └── examples/               # ⚠️ NOT maintained, ignore
├── deploy.sh                   # ⭐ Production deployment script
├── logs.sh                     # ⭐ Log viewing tool
└── CLAUDE.md                   # This file
```

## Development Tips & Important Notes

1. **Deployment**: ALWAYS use `./deploy.sh` for production deployment
   - Handles git operations, Docker build from project root, health checks
   - Manual docker commands will break (missing label_studio_ml modifications)

2. **Logging**: Use `./logs.sh -f` to monitor production logs in real-time
   - Logs persisted to `/var/log/invoice-extractor.log` on remote server
   - Container restart preserves logs (file-based, not docker logs)

3. **Model Version Management**:
   - Format: `"processor_type|model_name"` (e.g., `"gemini|gemini-2.5-flash"`)
   - Switch models at runtime via `/predict` endpoint's `model_version` parameter
   - List available versions: `GET /versions`

4. **Error Handling**:
   - Use `ModelResponse` class for all predictions
   - Supports error categorization and per-task error tracking
   - Errors returned in response alongside predictions

5. **Configuration Priority**:
   1. Runtime parameters (in API request)
   2. Environment variables (in `.env`)
   3. Config files (`config/models.yaml`)

6. **IP Whitelist**:
   - Configured in `config/models.yaml` under `security.ip_whitelist`
   - Uses `check_ip_whitelist()` in `label_studio_ml/api.py`

7. **Testing Without API Calls**:
   - Set `DOCUMENT_PROCESSOR=mock` to use mock processor
   - Useful for testing logic without consuming API quota

8. **Docker Build Context**:
   - Build from **project root** (not invoice_extractor/)
   - Required to include modified `label_studio_ml/` module
   - `deploy.sh` handles this automatically

## Recent Critical Fixes

1. **`/analyze` endpoint 404 fix** (commit 5721a26):
   - Problem: Docker installed label-studio-ml from upstream GitHub (no /analyze)
   - Solution: Modified Dockerfile to install from local modified version
   - Deploy from project root to include label_studio_ml/

2. **Log persistence**:
   - Container logs redirect to `/var/log/invoice-extractor.log`
   - Survives container restarts, accessible via `logs.sh`

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `/analyze` returns 404 | Rebuild with `./deploy.sh` (don't use manual docker build) |
| Logs not showing | Check container started with nohup redirect (use `./deploy.sh`) |
| Model version not switching | Check format: `"processor_type\|model_name"` |
| IP blocked | Add IP to `config/models.yaml` security.ip_whitelist |
| API quota exceeded | Switch to mock processor for testing |