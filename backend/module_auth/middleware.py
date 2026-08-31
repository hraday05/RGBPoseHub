"""
Module Auth — JWT Middleware & Helpers
Authentication middleware for protecting endpoints.
"""
import json
from datetime import datetime, timezone
from functools import wraps
from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app import db
from module_auth.models import User, ActivityLog


def log_activity(user_id, action, category='system', description=None, metadata=None, status='success'):
    """
    Log a user activity event.
    This is the central logging function used across all modules.
    """
    try:
        log_entry = ActivityLog(
            user_id=user_id,
            action=action,
            category=category,
            description=description,
            metadata_json=json.dumps(metadata) if metadata else None,
            ip_address=request.remote_addr if request else None,
            status=status,
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
    except Exception as e:
        db.session.rollback()
        print(f"[ActivityLog Error] {e}")
        return None


def get_current_user():
    """Get the currently authenticated user from JWT."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return User.query.get(user_id)
    except Exception:
        return None


def admin_required(fn):
    """Decorator to require admin role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return {'error': 'Admin access required'}, 403
        return fn(*args, **kwargs)
    return wrapper
