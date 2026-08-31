"""
Module Auth — API Routes
Handles user registration, login, 2FA, sessions, and activity history.
"""
import json
import uuid
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
import bcrypt
from app import db
from module_auth.models import User, Session, ActivityLog, TwoFactorSecret
from module_auth.two_factor import TwoFactorAuth
from module_auth.middleware import log_activity

auth_bp = Blueprint('auth', __name__)


# ─── Registration ────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    
    # Validation
    if not email or not username or not password:
        return jsonify({'error': 'Email, username, and password are required'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user with explicit UUID
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash=password_hash,
        full_name=full_name or username,
    )
    db.session.add(user)
    
    # Generate 2FA secret
    secret = TwoFactorAuth.generate_secret()
    two_factor = TwoFactorSecret(id=str(uuid.uuid4()), user_id=user_id, secret=secret)
    db.session.add(two_factor)
    
    db.session.commit()
    
    # Generate QR code for 2FA setup
    provisioning_uri = TwoFactorAuth.get_provisioning_uri(secret, email)
    qr_base64 = TwoFactorAuth.generate_qr_code_base64(provisioning_uri)
    
    # Log registration
    log_activity(user.id, 'register', 'auth', f'User {username} registered successfully')
    
    return jsonify({
        'message': 'Registration successful. Please set up 2FA.',
        'user': user.to_dict(),
        'two_factor': {
            'secret': secret,
            'qr_code': qr_base64,
            'provisioning_uri': provisioning_uri,
        }
    }), 201


# ─── 2FA Setup Verification ─────────────────────────────────

@auth_bp.route('/verify-2fa-setup', methods=['POST'])
def verify_2fa_setup():
    """Verify 2FA setup by confirming the first OTP code."""
    data = request.get_json()
    user_id = data.get('user_id')
    otp_code = data.get('otp_code', '').strip()
    
    if not user_id or not otp_code:
        return jsonify({'error': 'User ID and OTP code are required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    two_factor = TwoFactorSecret.query.filter_by(user_id=user_id).first()
    if not two_factor:
        return jsonify({'error': '2FA secret not found'}), 404
    
    if TwoFactorAuth.verify_otp(two_factor.secret, otp_code):
        two_factor.is_verified = True
        two_factor.verified_at = datetime.now(timezone.utc)
        user.is_2fa_enabled = True
        db.session.commit()
        
        log_activity(user.id, '2fa_setup_complete', 'auth', '2FA successfully configured')
        
        return jsonify({'message': '2FA setup verified successfully', 'is_2fa_enabled': True})
    else:
        log_activity(user.id, '2fa_setup_failed', 'auth', 'Invalid OTP during 2FA setup', status='failure')
        return jsonify({'error': 'Invalid OTP code. Please try again.'}), 400


# ─── Login ───────────────────────────────────────────────────

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with email/username and password.
    If 2FA is enabled, returns a pending status requiring OTP verification.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    login_id = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not login_id or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Find user by email or username
    user = User.query.filter(
        (User.email == login_id) | (User.username == login_id)
    ).first()
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403
    
    # Check if 2FA is enabled
    if user.is_2fa_enabled:
        # Return pending status — client must call /verify-2fa-login
        log_activity(user.id, 'login_password_verified', 'auth', 'Password verified, awaiting 2FA')
        return jsonify({
            'message': '2FA verification required',
            'requires_2fa': True,
            'user_id': user.id,
        }), 200
    else:
        # No 2FA — issue tokens directly
        return _complete_login(user)


@auth_bp.route('/verify-2fa-login', methods=['POST'])
def verify_2fa_login():
    """Verify 2FA code during login and issue JWT tokens."""
    data = request.get_json()
    user_id = data.get('user_id')
    otp_code = data.get('otp_code', '').strip()
    
    if not user_id or not otp_code:
        return jsonify({'error': 'User ID and OTP code are required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    two_factor = TwoFactorSecret.query.filter_by(user_id=user_id).first()
    if not two_factor:
        return jsonify({'error': '2FA not configured'}), 400
    
    if TwoFactorAuth.verify_otp(two_factor.secret, otp_code):
        return _complete_login(user)
    else:
        log_activity(user.id, '2fa_login_failed', 'auth', 'Invalid OTP during login', status='failure')
        return jsonify({'error': 'Invalid OTP code'}), 401


def _complete_login(user):
    """Complete the login process by issuing JWT tokens and logging the session."""
    jti = str(uuid.uuid4())
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'jti': jti, 'role': user.role, 'username': user.username}
    )
    refresh_token = create_refresh_token(identity=user.id)
    
    # Create session record
    session = Session(
        user_id=user.id,
        token_jti=jti,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:500],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.session.add(session)
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    
    log_activity(user.id, 'login_success', 'auth', f'Login from {request.remote_addr}')
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
    }), 200


# ─── Token Refresh ───────────────────────────────────────────

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh an access token."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    jti = str(uuid.uuid4())
    access_token = create_access_token(
        identity=user_id,
        additional_claims={'jti': jti, 'role': user.role, 'username': user.username}
    )
    
    return jsonify({'access_token': access_token}), 200


# ─── Logout ──────────────────────────────────────────────────

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout — revoke current session."""
    user_id = get_jwt_identity()
    jwt_data = get_jwt()
    jti = jwt_data.get('jti', '')
    
    session = Session.query.filter_by(token_jti=jti, is_active=True).first()
    if session:
        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        db.session.commit()
    
    log_activity(user_id, 'logout', 'auth', 'User logged out')
    
    return jsonify({'message': 'Logged out successfully'}), 200


# ─── Profile ─────────────────────────────────────────────────

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if 'full_name' in data:
        user.full_name = data['full_name']
    
    db.session.commit()
    log_activity(user_id, 'profile_update', 'auth', 'Profile updated')
    
    return jsonify({'user': user.to_dict()}), 200


# ─── Activity History ─────────────────────────────────────────

@auth_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    """Get complete activity history for the current user."""
    user_id = get_jwt_identity()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category', None)
    
    query = ActivityLog.query.filter_by(user_id=user_id)
    
    if category:
        query = query.filter_by(category=category)
    
    query = query.order_by(ActivityLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'history': [log.to_dict() for log in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page,
    }), 200


# ─── Sessions Management ─────────────────────────────────────

@auth_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    """Get all active sessions for the current user."""
    user_id = get_jwt_identity()
    
    sessions = Session.query.filter_by(
        user_id=user_id, is_active=True
    ).order_by(Session.created_at.desc()).all()
    
    return jsonify({
        'sessions': [s.to_dict() for s in sessions],
        'total': len(sessions),
    }), 200


@auth_bp.route('/sessions/<session_id>/revoke', methods=['POST'])
@jwt_required()
def revoke_session(session_id):
    """Revoke a specific session."""
    user_id = get_jwt_identity()
    
    session = Session.query.filter_by(id=session_id, user_id=user_id).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    session.is_active = False
    session.revoked_at = datetime.now(timezone.utc)
    db.session.commit()
    
    log_activity(user_id, 'session_revoked', 'auth', f'Session {session_id} revoked')
    
    return jsonify({'message': 'Session revoked'}), 200


# ─── Dashboard Stats ──────────────────────────────────────────

@auth_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Get dashboard statistics for the current user."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get activity counts
    total_logins = ActivityLog.query.filter_by(user_id=user_id, action='login_success').count()
    total_analyses = ActivityLog.query.filter_by(user_id=user_id, action='image_analysis').count()
    total_uploads = ActivityLog.query.filter_by(user_id=user_id, action='image_upload').count()
    
    # Recent activity (last 5)
    recent = ActivityLog.query.filter_by(user_id=user_id)\
        .order_by(ActivityLog.created_at.desc()).limit(5).all()
    
    # Active sessions count
    active_sessions = Session.query.filter_by(user_id=user_id, is_active=True).count()
    
    return jsonify({
        'stats': {
            'total_logins': total_logins,
            'total_analyses': total_analyses,
            'total_uploads': total_uploads,
            'active_sessions': active_sessions,
            'member_since': user.created_at.isoformat() if user.created_at else None,
        },
        'recent_activity': [log.to_dict() for log in recent],
    }), 200
