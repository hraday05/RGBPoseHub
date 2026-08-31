import unittest
import json
from app import create_app
from extensions import db
from module_auth.models import User, ActivityLog, Session
from module_auth.two_factor import TwoFactorAuth


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_registration_flow(self):
        """Test user registration and 2FA secret generation."""
        res = self.client.post('/api/auth/register', json={
            'email': 'researcher@example.com',
            'username': 'researcher1',
            'password': 'Password123!',
            'full_name': 'Test Researcher'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn('user', data)
        self.assertIn('two_factor', data)
        self.assertTrue(data['two_factor']['secret'])

    def test_2fa_verification_and_login(self):
        """Test 2FA setup verification and login challenge."""
        # 1. Register
        reg_res = self.client.post('/api/auth/register', json={
            'email': 'user2@example.com',
            'username': 'user2',
            'password': 'Password123!',
        })
        reg_data = reg_res.get_json()
        user_id = reg_data['user']['id']
        secret = reg_data['two_factor']['secret']

        # Generate valid OTP
        otp_code = TwoFactorAuth.get_current_otp(secret)

        # 2. Verify 2FA Setup
        setup_res = self.client.post('/api/auth/verify-2fa-setup', json={
            'user_id': user_id,
            'otp_code': otp_code
        })
        self.assertEqual(setup_res.status_code, 200)

        # 3. Login (Password phase)
        login_res = self.client.post('/api/auth/login', json={
            'email': 'user2@example.com',
            'password': 'Password123!'
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.get_json().get('requires_2fa'))

        # 4. Login (2FA verification phase)
        otp_code2 = TwoFactorAuth.get_current_otp(secret)
        verify_res = self.client.post('/api/auth/verify-2fa-login', json={
            'user_id': user_id,
            'otp_code': otp_code2
        })
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn('access_token', verify_res.get_json())


if __name__ == '__main__':
    unittest.main()
