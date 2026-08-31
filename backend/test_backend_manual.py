"""
RGB-Pose Hub — Backend Verification Script
Tests all 3 backend modules without needing a browser frontend.
Fully idempotent — can be run repeatedly!
"""
import uuid
from app import create_app, db
from module_auth.models import User, ActivityLog, Session
from module_auth.two_factor import TwoFactorAuth

def run_backend_test():
    print("=" * 60)
    print("🚀 RGB-Pose Hub Backend Verification Suite")
    print("=" * 60)

    app = create_app('development')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    client = app.test_client()

    with app.app_context():
        db.create_all()

        # Generate unique credentials for idempotent test execution
        unique_suffix = uuid.uuid4().hex[:6]
        test_email = f"researcher_{unique_suffix}@example.com"
        test_username = f"user_{unique_suffix}"
        test_password = "SecurePassword123!"

        # 1. Health Check
        print("\n[1/5] Testing Health Check Endpoint...")
        res = client.get('/api/health')
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        print(f"  ✓ Health Check OK: {res.get_json()}")

        # 2. Registration & 2FA Secret Generation
        print("\n[2/5] Testing User Registration & 2FA Setup...")
        res = client.post('/api/auth/register', json={
            'email': test_email,
            'username': test_username,
            'password': test_password,
            'full_name': f"Researcher {unique_suffix}"
        })
        assert res.status_code == 201, f"Registration failed: {res.get_json()}"
        reg_data = res.get_json()
        user_id = reg_data['user']['id']
        secret = reg_data['two_factor']['secret']
        print(f"  ✓ Registered User: {test_username} ({test_email})")
        print(f"  ✓ Generated User ID: {user_id}")
        print(f"  ✓ Generated 2FA Secret: {secret}")
        print(f"  ✓ Provisioning URI: {reg_data['two_factor']['provisioning_uri'][:40]}...")

        # 3. 2FA Setup Verification
        print("\n[3/5] Testing 2FA Setup Verification (PyOTP)...")
        otp = TwoFactorAuth.get_current_otp(secret)
        print(f"  Current 6-Digit OTP: {otp}")
        res = client.post('/api/auth/verify-2fa-setup', json={
            'user_id': user_id,
            'otp_code': otp
        })
        assert res.status_code == 200, f"2FA setup failed: {res.get_json()}"
        print(f"  ✓ 2FA Configured: {res.get_json()}")

        # 4. Login & 2FA Challenge
        print("\n[4/5] Testing Login & 2FA Verification...")
        # Step A: Password Check
        res = client.post('/api/auth/login', json={
            'email': test_email,
            'password': test_password
        })
        assert res.status_code == 200 and res.get_json().get('requires_2fa'), "Login password check failed"
        print("  ✓ Step A: Password verified, 2FA challenge triggered")

        # Step B: OTP Check
        otp2 = TwoFactorAuth.get_current_otp(secret)
        res = client.post('/api/auth/verify-2fa-login', json={
            'user_id': user_id,
            'otp_code': otp2
        })
        assert res.status_code == 200, f"2FA verification failed: {res.get_json()}"
        token = res.get_json()['access_token']
        print(f"  ✓ Step B: 2FA Verified! JWT Access Token issued: {token[:30]}...")

        # 5. Protected Activity History & Stats
        print("\n[5/5] Testing Activity Logging & History Endpoint...")
        headers = {'Authorization': f'Bearer {token}'}
        res = client.get('/api/auth/history', headers=headers)
        assert res.status_code == 200, "History request failed"
        history = res.get_json()['history']
        print(f"  ✓ Recorded Activity Logs ({len(history)} entries):")
        for h in history:
            print(f"     - [{h['category'].upper()}] {h['action']}: {h['description']}")

        print("\n" + "=" * 60)
        print("🎉 ALL BACKEND MODULES (Auth, 2FA, History) VERIFIED 100% WORKING!")
        print("=" * 60)

if __name__ == '__main__':
    run_backend_test()
