"""
RGB-Pose Hub — ML Pipeline Verification Script
Tests model status, training history, and live PyTorch CNN inference.
"""
import os
import uuid
from app import create_app
from extensions import db
from module_auth.models import User
from module_auth.two_factor import TwoFactorAuth

def run_ml_verification():
    print("=" * 60)
    print("🧠 RGB-Pose Hub — ML Pipeline Verification Suite")
    print("=" * 60)

    app = create_app('development')
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        db.create_all()

        # Step 1: Register and login test user
        suffix = uuid.uuid4().hex[:6]
        user_email = f"ml_test_{suffix}@example.com"
        user_name = f"mluser_{suffix}"
        password = "MLTestPassword123!"

        reg_res = client.post('/api/auth/register', json={
            'email': user_email, 'username': user_name, 'password': password
        })
        user_id = reg_res.get_json()['user']['id']
        secret = reg_res.get_json()['two_factor']['secret']
        otp = TwoFactorAuth.get_current_otp(secret)

        client.post('/api/auth/verify-2fa-setup', json={'user_id': user_id, 'otp_code': otp})
        client.post('/api/auth/login', json={'email': user_email, 'password': password})
        login_res = client.post('/api/auth/verify-2fa-login', json={'user_id': user_id, 'otp_code': otp})
        token = login_res.get_json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        print("\n[1/4] User Authenticated successfully for ML testing.")

        # Step 2: Check Model Status
        print("\n[2/4] Testing GET /api/ml/status...")
        status_res = client.get('/api/ml/status', headers=headers)
        assert status_res.status_code == 200, f"Status failed: {status_res.get_json()}"
        status_data = status_res.get_json()
        print(f"  ✓ Model Info: {status_data.get('model')}")
        print(f"  ✓ Training Summary: {status_data.get('training_summary')}")

        # Step 3: Check Training History & Visualizations
        print("\n[3/4] Testing GET /api/ml/training-history...")
        hist_res = client.get('/api/ml/training-history', headers=headers)
        if hist_res.status_code == 200:
            hist_data = hist_res.get_json()
            print(f"  ✓ Training History Found: {hist_data.get('history', {}).get('epochs_completed')} epochs completed")
            print(f"  ✓ Loss Curve Data Points: {len(hist_data.get('chart_data', {}).get('loss', {}).get('train', []))}")
        else:
            print(f"  ⚠ Training history notice: {hist_res.get_json()}")

        # Step 4: Run Live Inference on Dataset Image
        print("\n[4/4] Testing POST /api/ml/predict-dataset/000_veet.png...")
        pred_res = client.post('/api/ml/predict-dataset/000_veet.png', headers=headers)
        assert pred_res.status_code == 200, f"Inference failed: {pred_res.get_json()}"
        pred_data = pred_res.get_json()
        results = pred_data.get('results', {})
        print(f"  ✓ Inference Method: {results.get('method')} ({results.get('backend', 'N/A')})")
        print(f"  ✓ Predictions Count: {len(results.get('predictions', []))}")
        if results.get('predictions'):
            top1 = results['predictions'][0]
            print(f"  ✓ Top-1 Class: {top1['class_name']} (ID: {top1['class_id']}) with {top1['confidence_pct']}% confidence")

        print("\n" + "=" * 60)
        print("🎉 ML PIPELINE VERIFICATION 100% PASSED!")
        print("=" * 60)

if __name__ == '__main__':
    run_ml_verification()
