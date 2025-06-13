from typing import List
from invoice_extractor.processors.base import DocumentProcessor
from invoice_extractor.processors.gemini import GeminiProcessor
from invoice_extractor.processors.mock import MockProcessor

class DocumentProcessorFactory:
    """Factory for creating document processors"""
    
    _processors = {
        'gemini': GeminiProcessor,
        'mock': MockProcessor,
    }
    
    @classmethod
    def create_processor(cls, processor_type: str, **kwargs) -> DocumentProcessor:
        """Create a document processor of the specified type"""
        if processor_type not in cls._processors:
            raise ValueError(f"Unknown processor type: {processor_type}. Available types: {list(cls._processors.keys())}")
        
        processor_class = cls._processors[processor_type]
        return processor_class(**kwargs)
    
    @classmethod
    def register_processor(cls, name: str, processor_class: type):
        """Register a new processor type"""
        if not issubclass(processor_class, DocumentProcessor):
            raise ValueError("Processor class must inherit from DocumentProcessor")
        cls._processors[name] = processor_class
    
    @classmethod
    def get_available_processors(cls) -> List[str]:
        """Get list of available processor types"""
        return list(cls._processors.keys()) 