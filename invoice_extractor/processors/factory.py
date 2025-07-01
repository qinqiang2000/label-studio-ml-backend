from typing import List
import logging
from processors.base import DocumentProcessor
from processors.gemini import GeminiProcessor
from processors.mock import MockProcessor

# Try to import OpenAI processor
try:
    from processors.openai import OpenAIDocumentProcessor
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import config manager
try:
    from config.manager import config_manager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentProcessorFactory:
    """Factory for creating document processors"""
    
    _processors = {
        'gemini': GeminiProcessor,
        'mock': MockProcessor,
    }
    
    # Add OpenAI processor if available
    if OPENAI_AVAILABLE:
        _processors['openai'] = OpenAIDocumentProcessor
    
    @classmethod
    def create_processor(cls, processor_type: str, **kwargs) -> DocumentProcessor:
        """Create a document processor of the specified type"""
        if processor_type not in cls._processors:
            raise ValueError(f"Unknown processor type: {processor_type}. Available types: {list(cls._processors.keys())}")
        
        # 如果配置管理器可用，从配置中获取默认模型
        if CONFIG_MANAGER_AVAILABLE:
            try:
                # 如果kwargs中没有指定model_name，从配置获取默认值
                if 'model_name' not in kwargs:
                    default_model = config_manager.get_default_model(processor_type)
                    if default_model:
                        kwargs['model_name'] = default_model
                        logger.info(f"Using default model for {processor_type}: {default_model}")
                
            except Exception as e:
                logger.warning(f"Failed to get default model from config: {e}")
        
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
        # 如果配置管理器可用，返回启用的处理器
        if CONFIG_MANAGER_AVAILABLE:
            try:
                return config_manager.get_available_processors()
            except Exception as e:
                logger.warning(f"Failed to get available processors from config: {e}")
        
        # 否则返回所有注册的处理器
        return list(cls._processors.keys()) 