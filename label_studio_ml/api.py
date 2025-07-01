import hmac
import logging
import os

from flask import Flask, request, jsonify, Response

from .response import ModelResponse
from .model import LabelStudioMLBase
from .exceptions import exception_handler

logger = logging.getLogger(__name__)

_server = Flask(__name__)
MODEL_CLASS = LabelStudioMLBase
BASIC_AUTH = None


def init_app(model_class, basic_auth_user=None, basic_auth_pass=None):
    global MODEL_CLASS
    global BASIC_AUTH

    if not issubclass(model_class, LabelStudioMLBase):
        raise ValueError('Inference class should be the subclass of ' + LabelStudioMLBase.__class__.__name__)

    MODEL_CLASS = model_class
    basic_auth_user = basic_auth_user or os.environ.get('BASIC_AUTH_USER')
    basic_auth_pass = basic_auth_pass or os.environ.get('BASIC_AUTH_PASS')
    if basic_auth_user and basic_auth_pass:
        BASIC_AUTH = (basic_auth_user, basic_auth_pass)

    return _server


@_server.route('/predict', methods=['POST'])
@exception_handler
def _predict():
    """
    Predict tasks

    Example request:
    request = {
            'tasks': tasks,
            'model_version': model_version,
            'project': '{project.id}.{int(project.created_at.timestamp())}',
            'label_config': project.label_config,
            'params': {
                'login': project.task_data_login,
                'password': project.task_data_password,
                'context': context,
            },
        }

    @return:
    Predictions in LS format
    """
    data = request.json
    tasks = data.get('tasks')
    label_config = data.get('label_config')
    project = str(data.get('project'))
    project_id = project.split('.', 1)[0] if project else None
    params = data.get('params', {})
    context = params.pop('context', {})

    model = MODEL_CLASS(project_id=project_id,
                        label_config=label_config)

    # model.use_label_config(label_config)
    logger.info(f"API: Starting prediction for {len(tasks) if tasks else 0} tasks")

    response = model.predict(tasks, context=context, **params)
    logger.info(f"API: Received response from model, type: {type(response)}")

    # if there is no model version we will take the default
    if isinstance(response, ModelResponse):
        logger.info(f"API: Processing ModelResponse - has_errors: {response.has_errors()}, predictions_count: {len(response.predictions)}")
        
        if not response.has_model_version():
            mv = model.model_version
            if mv:
                response.set_version(str(mv))
        else:
            response.update_predictions_version()

        # 序列化ModelResponse对象
        response_dict = response.model_dump()
        logger.info(f"API: Serialized response - predictions: {len(response_dict.get('predictions', []))}, errors: {len(response_dict.get('errors', []) or [])}")
        
        # 构建最终响应，包含预测结果和错误信息
        final_response = {
            'predictions': response_dict.get('predictions', []),
            'model_version': response_dict.get('model_version')
        }
        
        # 如果有错误信息，添加到响应中
        if response_dict.get('errors'):
            final_response['errors'] = response_dict['errors']
            
        logger.info(f"API: Final response structure - predictions: {len(final_response.get('predictions', []))}, errors: {len(final_response.get('errors', []) or [])}")
        
        return jsonify({'results': final_response})
    else:
        # 向后兼容：处理非ModelResponse格式的响应
        logger.info(f"API: Processing legacy response format")
        res = response
        if res is None:
            res = []

        if isinstance(res, dict):
            res = response.get("predictions", response)

        return jsonify({'results': res})


@_server.route('/setup', methods=['POST'])
@exception_handler
def _setup():
    data = request.json
    project_id = data.get('project').split('.', 1)[0]
    label_config = data.get('schema')
    extra_params = data.get('extra_params')
    model = MODEL_CLASS(project_id=project_id,
                        label_config=label_config)

    if extra_params:
        model.set_extra_params(extra_params)

    model_version = model.get('model_version')
    return jsonify({'model_version': model_version})


TRAIN_EVENTS = (
    'ANNOTATION_CREATED',
    'ANNOTATION_UPDATED',
    'ANNOTATION_DELETED',
    'START_TRAINING'
)


@_server.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    event = data.pop('action')
    if event not in TRAIN_EVENTS:
        return jsonify({'status': 'Unknown event'}), 200
    project_id = str(data['project']['id'])
    label_config = data['project']['label_config']
    model = MODEL_CLASS(project_id, label_config=label_config)
    result = model.fit(event, data)

    try:
        response = jsonify({'result': result, 'status': 'ok'})
    except Exception as e:
        response = jsonify({'error': str(e), 'status': 'error'})

    return response, 201


@_server.route('/health', methods=['GET'])
@_server.route('/', methods=['GET'])
@exception_handler
def health():
    return jsonify({
        'status': 'UP',
        'model_class': MODEL_CLASS.__name__
    })


@_server.route('/analyze', methods=['POST'])
@exception_handler
def _analyze():
    """
    Analyze Excel content

    Example request:
    request = {
        'excel_content': '<base64_encoded_excel_content>',
        'excel_filename': '<filename.xlsx>',
        'project': '<project.id>.<timestamp>',
        'label_config': '<xml_config>',
        'params': {
            'context': {},
            'analysis_type': 'evaluation',
            'extra_params': {}
        }
    }

    @return:
    Analysis result in markdown format
    """
    data = request.json
    excel_content = data.get('excel_content')
    excel_filename = data.get('excel_filename')
    project = str(data.get('project'))
    project_id = project.split('.', 1)[0] if project else None
    label_config = data.get('label_config')
    params = data.get('params', {})
    context = params.get('context', {})
    analysis_type = params.get('analysis_type', 'evaluation')
    prompt = params.get('prompt', None)
    extra_params = params.get('extra_params', {})
    
    try:
        # Validate required fields
        if not excel_content:
            return jsonify({
                'status': 'error',
                'error': 'excel_content is required'
            }), 400
        
        if not excel_filename:
            return jsonify({
                'status': 'error',
                'error': 'excel_filename is required'
            }), 400

        model = MODEL_CLASS(project_id=project_id, label_config=label_config)

        logger.info(f"API: Starting analysis for excel file: {excel_filename}")

        # Call the analyze method
        analysis_result = model.analyze_excel(
            excel_content=excel_content,
            filename=excel_filename,
            context=context,
            analysis_type=analysis_type,
            prompt=prompt,
            **extra_params
        )

        logger.info(f"API: Received analysis result from model")

        return jsonify({
            'status': 'success',
            'analysis_result': analysis_result,
            'metadata': {
                'model_version': str(model.model_version)
            }
        })

    except Exception as e:
        logger.error(f"API: Error in analyze endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@_server.route('/versions', methods=['GET'])
@exception_handler
def _get_versions():
    """
    Get available model versions

    Example request:
    GET /versions

    @return:
    Available model versions in JSON format
    """
    data = request.json if request.method == 'POST' else request.args
    project = data.get('project') if data else None
    project_id = project.split('.', 1)[0] if project else None
    
    try:
        model = MODEL_CLASS(project_id=project_id, label_config=None)
        versions_info = model.get_versions()
        
        logger.info(f"API: Retrieved versions info with {len(versions_info.get('versions', []))} versions")
        
        return jsonify(versions_info)
        
    except Exception as e:
        logger.error(f"API: Error in versions endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'versions': [],
            'current_version': {},
            'total_count': 0,
            'error': str(e)
        }), 500


@_server.route('/metrics', methods=['GET'])
@exception_handler
def metrics():
    return jsonify({})


@_server.errorhandler(FileNotFoundError)
def file_not_found_error_handler(error):
    logger.warning('Got error: ' + str(error))
    return str(error), 404


@_server.errorhandler(AssertionError)
def assertion_error(error):
    logger.error(str(error), exc_info=True)
    return str(error), 500


@_server.errorhandler(IndexError)
def index_error(error):
    logger.error(str(error), exc_info=True)
    return str(error), 500


def safe_str_cmp(a, b):
    return hmac.compare_digest(a, b)


@_server.before_request
def check_auth():
    if BASIC_AUTH is not None:

        auth = request.authorization
        if not auth or not (safe_str_cmp(auth.username, BASIC_AUTH[0]) and safe_str_cmp(auth.password, BASIC_AUTH[1])):
            return Response('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})


@_server.before_request
def log_request_info():
    logger.debug('Request headers: %s', request.headers)
    logger.debug('Request body: %s', request.get_data())


@_server.after_request
def log_response_info(response):
    logger.debug('Response status: %s', response.status)
    logger.debug('Response headers: %s', response.headers)
    logger.debug('Response body: %s', response.get_data())
    return response
