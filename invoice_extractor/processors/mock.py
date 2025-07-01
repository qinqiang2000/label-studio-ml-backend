import logging
from processors.base import DocumentProcessor
from utils import get_mock_invoice_data

logger = logging.getLogger(__name__)

class MockProcessor(DocumentProcessor):
    """Mock processor for testing purposes"""
    
    def __init__(self, model_name: str = "mock-v1.0", **kwargs):
        """Initialize mock processor with optional model name"""
        self.model_name = model_name
        logger.info(f"MockProcessor initialized with model: {model_name}")
    
    def process_document(self, file_path: str, instruction: str) -> str:
        logger.info('Using mock data for document processing')
        return get_mock_invoice_data()
    
    def get_model_version(self) -> str:
        return f"mock|{self.model_name}" 