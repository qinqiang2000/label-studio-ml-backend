from typing import Type, Dict, Optional, List, Tuple, Any, Union
from pydantic import BaseModel, confloat, Field
from label_studio_sdk.label_interface.objects import PredictionValue
from typing import Union, List


# one or multiple predictions per task
SingleTaskPredictions = Union[List[PredictionValue], PredictionValue]


class ModelResponse(BaseModel):
    """ Model response with predictions for Label Studio, used in /predict API endpoint
    """
    class Config:
        protected_namespaces = ('__.*__', '_.*')  # Excludes 'model_'

    model_version: Optional[str] = None
    predictions: List[SingleTaskPredictions]
    errors: Optional[List[Dict[str, Any]]] = None  # 新增错误信息字段

    def has_model_version(self) -> bool:
        return bool(self.model_version)

    def update_predictions_version(self) -> None:
        """
        """
        for prediction in self.predictions:
            if isinstance(prediction, PredictionValue):
                prediction = [prediction]
            for p in prediction:
                if not p.model_version:
                    p.model_version = self.model_version
    
    def set_version(self, version: str) -> None:
        """
        """
        self.model_version = version
        # Set the version for each prediction
        self.update_predictions_version()
    
    def add_error(self, task_index: int, task_id: str, error_message: str, error_type: str = "processing_error") -> None:
        """
        添加错误信息到响应中
        """
        if self.errors is None:
            self.errors = []
        
        self.errors.append({
            "task_index": task_index,
            "task_id": task_id,
            "error_type": error_type,
            "error_message": error_message
        })
    
    def has_errors(self) -> bool:
        """
        检查是否有错误信息
        """
        return self.errors is not None and len(self.errors) > 0
        
