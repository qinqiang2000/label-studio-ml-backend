"""
自定义API扩展模块
用于在标准label-studio-ml基础上添加自定义端点

测试注释：验证自动重启策略部署流程 - 2026-01-27
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
    # 强制设置正确的日志级别，确保业务日志能正常显示
    import logging
    import os
    final_log_level = os.getenv('LOG_LEVEL', 'INFO')
    logging.getLogger().setLevel(getattr(logging, final_log_level.upper()))
    logger.info(f"APP INIT: Final log level set to: {final_log_level}")

    # 使用标准的init_app创建基础应用
    app = base_init_app(model_class, **kwargs)

    # 强制设置Flask应用的日志级别
    app.logger.setLevel(getattr(logging, final_log_level.upper()))

    # 再次确认日志级别（Flask可能会重置）
    logging.getLogger().setLevel(getattr(logging, final_log_level.upper()))

    # 为所有相关的logger设置级别
    for logger_name in ['invoice_extractor', 'custom_api', 'model', '__main__']:
        specific_logger = logging.getLogger(logger_name)
        specific_logger.setLevel(getattr(logging, final_log_level.upper()))

    # 确保根logger有handler（如果没有的话）
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        import sys
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, final_log_level.upper()))
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, final_log_level.upper()))

    logger.info(f"APP INIT: After Flask init, log level confirmed: {final_log_level}")
    logger.info(f"APP INIT: Flask app logger level: {app.logger.getEffectiveLevel()}")

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

    @app.route('/test', methods=['GET'])
    def test_logging():
        """
        测试日志输出端点，包括显示最新commit信息

        Returns:
            JSON: 测试结果和commit信息
        """
        import subprocess
        import datetime

        # 强制设置日志级别为确保我们的日志能显示
        import logging
        root_logger = logging.getLogger()
        current_level = root_logger.getEffectiveLevel()
        app_level = app.logger.getEffectiveLevel()
        custom_api_level = logging.getLogger('custom_api').getEffectiveLevel()

        # 临时设置为INFO级别测试
        root_logger.setLevel(logging.INFO)
        app.logger.setLevel(logging.INFO)
        logging.getLogger('custom_api').setLevel(logging.INFO)

        logger.info("=== /test endpoint called ===")
        
        # 恢复原来的级别
        root_logger.setLevel(current_level)

        try:
            # 从环境变量获取git信息（在Docker中通过deploy.sh传入）
            import os
            commit_hash = os.getenv('GIT_COMMIT_HASH', 'unknown')
            commit_date = os.getenv('GIT_COMMIT_DATE', 'unknown')
            commit_message = os.getenv('GIT_COMMIT_MESSAGE', 'unknown')

            if commit_hash != 'unknown':
                logger.info(f"Current commit: {commit_hash}")
                logger.info(f"Commit date: {commit_date}")
                logger.info(f"Commit message: {commit_message}")
            else:
                logger.warning("Git info not available from environment variables")

        except Exception as git_error:
            logger.error(f"Failed to get git info: {git_error}")
            commit_hash = "unknown"
            commit_date = "unknown"
            commit_message = "unknown"

        # 测试模型相关日志
        try:
            logger.info("Testing model instantiation...")
            model_instance = model_class()
            logger.info(f"Model class: {model_class.__name__}")
            logger.info(f"Model version: {getattr(model_instance, 'model_version', 'unknown')}")
            logger.info("Model instantiation successful")

        except Exception as model_error:
            logger.error(f"Model instantiation failed: {model_error}")

        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Test completed at: {current_time}")
        logger.info("=== /test endpoint finished ===")

        return jsonify({
            'status': 'success',
            'message': 'Logging test completed - check logs for output',
            'timestamp': current_time,
            'git_info': {
                'commit_hash': commit_hash,
                'commit_date': commit_date,
                'commit_message': commit_message
            },
            'log_levels_tested': ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        })

    # 在这里可以继续添加更多自定义端点
    # 例如：
    # @app.route('/custom/endpoint', methods=['POST'])
    # def custom_endpoint():
    #     pass

    logger.info("Custom endpoints added: /versions, /model/info, /health/detailed, /test")