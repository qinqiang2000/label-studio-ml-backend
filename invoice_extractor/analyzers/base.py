from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAnalyzer(ABC):
    """Abstract base class for data analysis strategies"""
    
    @abstractmethod
    def analyze(self, data: Any, **kwargs) -> str:
        """
        Analyze data and return analysis result
        
        Args:
            data: The data to analyze
            **kwargs: Additional analysis parameters
            
        Returns:
            Analysis result as string
        """
        pass
    
    @abstractmethod
    def get_analyzer_info(self) -> Dict[str, str]:
        """
        Return analyzer information
        
        Returns:
            Dictionary containing analyzer metadata
        """
        pass 