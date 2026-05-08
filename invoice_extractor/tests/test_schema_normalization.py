import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from processors.gemini import GeminiProcessor
from google.genai import types


def test_gemini_normalizes_response_template_to_schema():
    processor = GeminiProcessor.__new__(GeminiProcessor)
    template_schema = {
        "header": {
            "basic": {
                "invoiceNumber": "",
                "totalAmount": "",
            }
        },
        "detail": {
            "detailOfGoodsOrServices": [
                {
                    "articleName": "",
                    "quantity": "",
                }
            ]
        },
    }

    normalized = processor._normalize_schema(template_schema)

    types.Schema.model_validate(normalized)

    assert normalized == {
        "type": "object",
        "properties": {
            "header": {
                "type": "object",
                "properties": {
                    "basic": {
                        "type": "object",
                        "properties": {
                            "invoiceNumber": {"type": "string"},
                            "totalAmount": {"type": "string"},
                        },
                    }
                },
            },
            "detail": {
                "type": "object",
                "properties": {
                    "detailOfGoodsOrServices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "articleName": {"type": "string"},
                                "quantity": {"type": "string"},
                            },
                        },
                    }
                },
            },
        },
    }


def test_gemini_preserves_valid_schema_while_normalizing_type_case():
    processor = GeminiProcessor.__new__(GeminiProcessor)
    schema = {
        "type": "OBJECT",
        "properties": {
            "items": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                    },
                },
            }
        },
        "required": ["items"],
    }

    normalized = processor._normalize_schema(schema)

    assert normalized == {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            }
        },
        "required": ["items"],
    }
