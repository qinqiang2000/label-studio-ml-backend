from abc import ABC, abstractmethod

class DocumentProcessor(ABC):
    """Abstract base class for document processing strategies"""
    
    @abstractmethod
    def process_document(self, file_path: str, instruction: str) -> str:
        """Process a document and return extracted information as JSON string"""
        pass
    
    @abstractmethod
    def get_model_version(self) -> str:
        """Return the model version identifier"""
        pass 