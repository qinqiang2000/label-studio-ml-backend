This guide describes the simplest way to start using ML backend with Label Studio.

## Running with Docker (Recommended)

1. Start Machine Learning backend on `http://localhost:9090` with prebuilt image:

```bash
docker-compose up
```

2. Validate that backend is running

```bash
$ curl http://localhost:9090/
{"status":"UP"}
```

3. Connect to the backend from Label Studio running on the same host: go to your project `Settings -> Machine Learning -> Add Model` and specify `http://localhost:9090` as a URL.


## Building from source (Advanced)

To build the ML backend from source, you have to clone the repository and build the Docker image:

```bash
docker-compose build
```

## Running without Docker (Advanced)

To run the ML backend without Docker, you have to clone the repository and install all dependencies using pip:

```bash
python -m venv ml-backend
source ml-backend/bin/activate
pip install -r requirements.txt
```

Then you can start the ML backend:

```bash
label-studio-ml start ./dir_with_your_model
```

# Configuration
Parameters can be set in `docker-compose.yml` before running the container.


The following common parameters are available:
- `BASIC_AUTH_USER` - specify the basic auth user for the model server
- `BASIC_AUTH_PASS` - specify the basic auth password for the model server
- `LOG_LEVEL` - set the log level for the model server
- `WORKERS` - specify the number of workers for the model server
- `THREADS` - specify the number of threads for the model server

# Customization

The ML backend can be customized by adding your own models and logic inside the `./dir_with_your_model` directory.

# Invoice Extractor

## Runtime Configuration API

The invoice extractor now supports runtime configuration parameters that can be passed through the API to customize AI model behavior on a per-request basis.

### Supported Runtime Config Parameters

- `temperature`: Control randomness of output (0.0-2.0)
- `response_schema`: Define expected JSON schema for structured output
- `response_mime_type`: Set response format ("application/json" or "text/plain")
- `max_output_tokens`: Maximum tokens in response
- `top_p`: Nucleus sampling parameter
- `top_k`: Top-k sampling parameter
- `seed`: Random seed for reproducible results
- `candidate_count`: Number of response candidates
- `stop_sequences`: Sequences that stop generation
- `presence_penalty`: Penalty for using already present tokens
- `frequency_penalty`: Penalty for token frequency
- `response_modalities`: Requested response modalities
- `thinking_config`: Deep thinking configuration

### API Usage Examples

#### 1. Basic Request (No Runtime Config)
```python
import requests

# Standard request - uses default/environment configuration
response = requests.post('/predict', json={
    'tasks': [task_data],
    'prompt': 'Extract invoice information'
})
```

#### 2. Request with Runtime Config
```python
import requests

# Request with custom runtime configuration
runtime_config = {
    "temperature": 0.2,
    "response_mime_type": "application/json",
    "response_schema": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total_amount": {"type": "number"},
            "date": {"type": "string"},
            "vendor": {"type": "string"}
        },
        "required": ["invoice_number", "total_amount", "date"]
    }
}

response = requests.post('/predict', json={
    'tasks': [task_data],
    'prompt': 'Extract invoice information',
    'runtime_config': runtime_config
})
```

#### 3. High-Precision Extraction
```python
# Configuration for high-precision, structured extraction
precision_config = {
    "temperature": 0.1,
    "response_mime_type": "application/json",
    "max_output_tokens": 2000,
    "seed": 12345,  # For reproducible results
    "response_schema": {
        "type": "object",
        "properties": {
            "invoice_data": {
                "type": "object",
                "properties": {
                    "header": {
                        "type": "object",
                        "properties": {
                            "invoice_number": {"type": "string"},
                            "date": {"type": "string"},
                            "due_date": {"type": "string"}
                        }
                    },
                    "vendor": {
                        "type": "object", 
                        "properties": {
                            "name": {"type": "string"},
                            "address": {"type": "string"}
                        }
                    },
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "total": {"type": "number"}
                            }
                        }
                    },
                    "totals": {
                        "type": "object",
                        "properties": {
                            "subtotal": {"type": "number"},
                            "tax": {"type": "number"},
                            "total": {"type": "number"}
                        }
                    }
                }
            }
        }
    }
}

response = requests.post('/predict', json={
    'tasks': [task_data],
    'runtime_config': precision_config
})
```

#### 4. Creative/Exploratory Mode
```python
# Configuration for more creative interpretation
creative_config = {
    "temperature": 0.7,
    "response_mime_type": "text/plain",
    "max_output_tokens": 1000,
    "top_p": 0.9
}

response = requests.post('/predict', json={
    'tasks': [task_data],
    'prompt': 'Extract and interpret all financial information from this document',
    'runtime_config': creative_config
})
```

### Configuration Priority

The system uses the following priority order for configuration:
1. **Runtime Config** (highest priority) - passed in API request
2. **Environment Variables** - set in deployment environment  
3. **Default Values** (lowest priority) - hardcoded defaults

### Error Handling

If runtime_config contains invalid parameters:
- Unknown parameters are logged as warnings but ignored
- Invalid parameter types are logged and the parameter is skipped
- The request continues with remaining valid parameters

### Logging

All runtime configuration usage is logged for debugging:
- Received parameters are logged at INFO level
- Applied configurations are logged at INFO level  
- Warnings for invalid/unknown parameters at WARNING level 