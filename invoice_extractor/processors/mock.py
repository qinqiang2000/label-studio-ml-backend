import logging
from processors.base import DocumentProcessor
from utils import get_mock_invoice_data

logger = logging.getLogger(__name__)

class MockProcessor(DocumentProcessor):
    """Mock processor for testing purposes"""
    
    def process_document(self, file_path: str, instruction: str) -> str:
        logger.info('Using mock data for document processing')
        return get_mock_invoice_data()
    
    def get_model_version(self) -> str:
        return "mock-processor-v1.0" 