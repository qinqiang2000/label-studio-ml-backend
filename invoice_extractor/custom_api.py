"""
自定义API扩展模块
用于在标准label-studio-ml基础上添加自定义端点
"""
import logging
from flask import jsonify, request
from label_studio_ml.api import init_app as base_init_app

logger = logging.getLogger(__name__)


def init_app_with_custom_endpoints(model_class, **kwargs):
    """
    初始化Flask应用并添加自定义端点

    Args:
        model_class: ML模型类
        **kwargs: 其他初始化参数

    Returns:
        Flask应用实例
    """
    # 使用标准的init_app创建基础应用
    app = base_init_app(model_class, **kwargs)

    # 添加自定义端点
    add_custom_endpoints(app, model_class)

    return app


def add_custom_endpoints(app, model_class):
    """
    添加所有自定义端点到Flask应用

    Args:
        app: Flask应用实例
        model_class: ML模型类
    """

    @app.route('/versions', methods=['GET'])
    def versions():
        """
        获取所有可用的模型版本

        Returns:
            JSON: 包含版本信息的响应
        """
        try:
            model_instance = model_class()
            versions_info = model_instance.get_versions()
            logger.info(f"Versions endpoint: Retrieved {len(versions_info.get('versions', []))} versions")
            return jsonify(versions_info)
        except Exception as e:
            logger.error(f"Versions endpoint error: {str(e)}", exc_info=True)
            return jsonify({
                'versions': [],
                'current_version': {},
                'total_count': 0,
                'error': str(e)
            }), 500

    @app.route('/model/info', methods=['GET'])
    def model_info():
        """
        获取当前模型的详细信息

        Returns:
            JSON: 模型信息
        """
        try:
            model_instance = model_class()
            # 假设模型有get_model_info方法，如果没有就返回基本信息
            if hasattr(model_instance, 'get_model_info'):
                info = model_instance.get_model_info()
            else:
                info = {
                    'model_class': model_class.__name__,
                    'model_dir': getattr(model_instance, 'MODEL_DIR', 'unknown'),
                    'status': 'active'
                }
            return jsonify(info)
        except Exception as e:
            logger.error(f"Model info endpoint error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/health/detailed', methods=['GET'])
    def detailed_health():
        """
        详细的健康检查端点

        Returns:
            JSON: 详细的健康状态信息
        """
        try:
            model_instance = model_class()
            health_info = {
                'status': 'healthy',
                'model_loaded': True,
                'model_class': model_class.__name__,
                'endpoints': [
                    '/setup', '/predict', '/train', '/health',
                    '/versions', '/model/info', '/health/detailed'
                ]
            }

            # 如果模型有健康检查方法，调用它
            if hasattr(model_instance, 'health_check'):
                additional_health = model_instance.health_check()
                health_info.update(additional_health)

            return jsonify(health_info)
        except Exception as e:
            logger.error(f"Detailed health endpoint error: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500

    # 在这里可以继续添加更多自定义端点
    # 例如：
    # @app.route('/custom/endpoint', methods=['POST'])
    # def custom_endpoint():
    #     pass

    logger.info("Custom endpoints added: /versions, /model/info, /health/detailed")