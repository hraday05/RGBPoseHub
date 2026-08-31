"""
RGB-Pose Hub — Flask Application Factory
Main entry point for the backend server.
"""
import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from config import config as config_map
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # Ensure required directories exist
    for folder in [app.config.get('UPLOAD_FOLDER', 'uploads'),
                   app.config.get('DATASET_FOLDER', 'dataset'),
                   app.config.get('MODEL_FOLDER', 'models')]:
        os.makedirs(folder, exist_ok=True)
    
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

    # Register blueprints
    from module_auth.routes import auth_bp
    from module_data.routes import data_bp
    from module_ml.routes import ml_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(ml_bp, url_prefix='/api/ml')

    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return {'status': 'ok', 'service': 'RGB-Pose Hub API', 'version': '2.0.0'}

    # Create database tables
    with app.app_context():
        from module_auth.models import User, Session, ActivityLog, TwoFactorSecret
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
