from flask import render_template, request, jsonify, current_app
from flask_wtf.csrf import CSRFError
from functools import wraps
import traceback

def init_error_handlers(app):
    def is_api_request():
        return (request.path.startswith('/api/') or
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.headers.get('Accept') == 'application/json')

    def handle_error(error, code, title, description):
        # Log request details for debugging
        if app.debug and code == 400:
            app.logger.error('Bad Request Details:')
            app.logger.error('Form Data: %s', dict(request.form))
            app.logger.error('Request Args: %s', dict(request.args))
            app.logger.error('Request Method: %s', request.method)

        if is_api_request():
            return jsonify({
                'error': {
                    'code': code,
                    'title': title,
                    'description': description
                }
            }), code
        return render_template('errors/error.html',
                           error_code=code,
                           error_title=title,
                           error_description=description,
                           debug=app.debug,
                           error_details=str(error) if app.debug else None), code

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        app.logger.warning('CSRF error occurred')
        if is_api_request():
            return jsonify({
                'error': {
                    'code': 400,
                    'title': 'CSRF Error',
                    'description': 'CSRF token missing or invalid'
                }
            }), 400
        return handle_error(
            error,
            400,
            'Bad Request',
            'CSRF validation failed. Please try again.'
        )

    @app.errorhandler(400)
    def bad_request_error(error):
        return handle_error(
            error,
            400,
            'Bad Request',
            'The server could not understand your request. Please check your input and try again.'
        )

    @app.errorhandler(401)
    def unauthorized_error(error):
        return handle_error(
            error,
            401,
            'Unauthorized',
            'You need to be logged in to access this resource.'
        )

    @app.errorhandler(403)
    def forbidden_error(error):
        return handle_error(
            error,
            403,
            'Forbidden',
            'You don\'t have permission to access this resource.'
        )

    @app.errorhandler(404)
    def not_found_error(error):
        return handle_error(
            error,
            404,
            'Page Not Found',
            'The page you\'re looking for doesn\'t exist or has been moved.'
        )

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return handle_error(
            error,
            405,
            'Method Not Allowed',
            'The method is not allowed for this endpoint.'
        )

    @app.errorhandler(429)
    def too_many_requests_error(error):
        return handle_error(
            error,
            429,
            'Too Many Requests',
            'You\'ve made too many requests. Please try again later.'
        )

    @app.errorhandler(500)
    def internal_server_error(error):
        # Log the error for debugging
        app.logger.error('Server Error: %s', str(error))
        app.logger.error('Traceback: %s', traceback.format_exc())
        
        return handle_error(
            error,
            500,
            'Internal Server Error',
            'Something went wrong on our end. We\'ve been notified and are working on it.'
        )

    @app.errorhandler(503)
    def service_unavailable_error(error):
        return handle_error(
            error,
            503,
            'Service Unavailable',
            'The service is temporarily unavailable. Please try again later.'
        )

def handle_errors(f):
    """
    Decorator to handle exceptions in routes and return appropriate error responses
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Log the error
            current_app.logger.error('Error in %s: %s', f.__name__, str(e))
            current_app.logger.error('Traceback: %s', traceback.format_exc())
            
            # Return error response
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': {
                        'code': 500,
                        'message': 'Internal Server Error',
                        'details': str(e) if current_app.debug else None
                    }
                }), 500
            return render_template('errors/error.html',
                                error_code=500,
                                error_title='Internal Server Error',
                                error_description='Something went wrong on our end.',
                                debug=current_app.debug,
                                error_details=str(e) if current_app.debug else None), 500
    return wrapper

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

def handle_validation_error(error):
    """Handler for validation errors"""
    if request.path.startswith('/api/'):
        return jsonify({
            'error': {
                'code': error.status_code,
                'message': 'Validation Error',
                'details': error.message
            }
        }), error.status_code
    return render_template('errors/error.html',
                         error_code=error.status_code,
                         error_title='Validation Error',
                         error_description=error.message), error.status_code