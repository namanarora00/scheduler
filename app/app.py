from flask import Flask, jsonify
from app.db import init_db
from app.routes.auth import auth_bp
from app.routes.organisation import org_bp
from app.routes.invite import invite_bp
from app.routes.cluster import cluster_bp
from app.routes.deployment import deployment_bp
from app.exceptions import ServiceException

app = Flask(__name__)
init_db(app) 

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(org_bp, url_prefix='/organisation')
app.register_blueprint(invite_bp, url_prefix='/invites')
app.register_blueprint(cluster_bp, url_prefix='/clusters')
app.register_blueprint(deployment_bp, url_prefix='/deployments')

# Global error handler for ServiceException
@app.errorhandler(ServiceException)
def handle_service_exception(error):
    response = {
        'error': True,
        'message': str(error),
        'error_code': error.error_code,
        'status_code': error.status_code
    }
    return jsonify(response), error.status_code

@app.errorhandler(500)
def handle_internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

