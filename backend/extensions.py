"""
RGB-Pose Hub — Flask Extensions Singleton
Centralized extension initialization to prevent dual-instance issues.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()
