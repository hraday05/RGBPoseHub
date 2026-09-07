"""
RGB-Pose Hub — Pose Backend Verification Suite
Tests:
  1. RGB-D Loader & Depth Unprojection (4-channel and dual-file pair)
  2. Track A: EfficientPose Deep Neural Network Forward Pass
  3. Track B: Geometric Correspondence & Proper PnP + RANSAC
  4. Unified Dual-Track Pose Estimation & Comparative Analysis
  5. 3D Point Cloud Generation for WebGL/Three.js
  6. Flask API Endpoints: /api/ml/estimate-pose & /api/ml/point-cloud-3d
"""

import os
import sys
import uuid
import numpy as np

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from create_sample_rgbd_images import create_sample_rgbd_images
from module_data.rgbd_utils import load_rgbd, unproject_depth_to_points, create_point_cloud_payload
from module_ml.track_a_efficientpose import TrackAEfficientPoseEngine
from module_ml.track_b_pnp import TrackBPnPEngine
from module_ml.pose_estimator import PoseEstimator
from app import create_app
from extensions import db


def run_tests():
    print("=" * 65)
    print("🚀 RGB-Pose Hub — Track A, Track B & 3D Point Cloud Test Suite")
    print("=" * 65)

    samples_dir = os.path.join(backend_dir, 'uploads', 'samples')
    os.makedirs(samples_dir, exist_ok=True)
    sample_file = os.path.join(samples_dir, 'sample_rgbd_box.png')
    depth_pair_file = os.path.join(samples_dir, 'sample_rgbd_box_depth.png')

    if not os.path.exists(sample_file):
        print("\nGenerating sample RGB-D test images...")
        create_sample_rgbd_images(samples_dir)

    # -------------------------------------------------------------
    # 1. Test RGB-D Loader & Pinhole Unprojection
    # -------------------------------------------------------------
    print("\n[1/6] Testing RGB-D Data Loader & Pinhole Depth Unprojection...")
    rgb, depth_m, info = load_rgbd(sample_file)
    print(f"  ✓ Loaded 4-channel image: {info['width']}x{info['height']} px, depth format: {info['format']}")
    print(f"  ✓ Valid depth range: {info['min_depth_m']:.2f}m to {info['max_depth_m']:.2f}m (mean: {info['mean_depth_m']:.2f}m)")
    assert depth_m.shape == (360, 480), f"Unexpected depth shape: {depth_m.shape}"

    rgb2, depth_m2, info2 = load_rgbd(sample_file, depth_path=depth_pair_file)
    print(f"  ✓ Loaded dual-file pair: format: {info2['format']}")

    points_3d, colors = unproject_depth_to_points(depth_m, rgb=rgb, stride=3)
    print(f"  ✓ Pinhole 3D Unprojection: generated {len(points_3d)} 3D points (stride=3)")
    assert len(points_3d) > 5000, "Unprojection produced insufficient points"
    assert points_3d.shape[1] == 3, "Points must be 3D (X, Y, Z)"
    assert colors.shape[1] == 3, "Colors must be 3D (R, G, B)"

    # -------------------------------------------------------------
    # 2. Test Track A: EfficientPose Engine
    # -------------------------------------------------------------
    print("\n[2/6] Testing Track A: EfficientPose Deep Neural Network...")
    engine_a = TrackAEfficientPoseEngine()
    res_a = engine_a.estimate_pose(rgb, depth_m, class_name="Cluttered Box Scene", confidence=94.5)
    
    assert res_a['status'] == 'success'
    t_a = res_a['translation_vector_m']
    print(f"  ✓ Translation vector: [{t_a['x']}, {t_a['y']}, {t_a['z']}] meters")
    print(f"  ✓ Rotation Euler: {res_a['rotation_euler_deg']['formatted']}")
    print(f"  ✓ Rotation Quaternion: {res_a['rotation_quaternion']['formatted']}")
    print(f"  ✓ 3D Bounding Box Volume: {res_a['bounding_box_3d']['volume_cm3']} cm³")
    assert len(res_a['pose_visualization']) > 500, "Missing base64 visualization"

    # -------------------------------------------------------------
    # 3. Test Track B: Geometric Correspondence & Proper PnP
    # -------------------------------------------------------------
    print("\n[3/6] Testing Track B: Geometric Correspondence & Proper PnP + RANSAC...")
    engine_b = TrackBPnPEngine()
    res_b = engine_b.estimate_pose(rgb, depth_m, class_name="Cluttered Box Scene", confidence=92.0)

    assert res_b['status'] == 'success'
    t_b = res_b['translation_vector_m']
    pnp_m = res_b['pnp_metrics']
    print(f"  ✓ Solver: {res_b['solver']}")
    print(f"  ✓ Translation vector: [{t_b['x']}, {t_b['y']}, {t_b['z']}] meters")
    print(f"  ✓ PnP Inliers: {pnp_m['inlier_count']}/{pnp_m['total_correspondences']} ({pnp_m['inlier_ratio_pct']}%)")
    print(f"  ✓ Mean Reprojection Error: {pnp_m['mean_reprojection_error_px']} px ({pnp_m['convergence']})")
    assert len(res_b['pose_visualization']) > 500, "Missing base64 visualization"

    # -------------------------------------------------------------
    # 4. Test Unified Pose Estimator & Comparison Analysis
    # -------------------------------------------------------------
    print("\n[4/6] Testing Unified Pose Estimator & Dual-Track Comparative Metrics...")
    estimator = PoseEstimator()
    dual_res = estimator.estimate_pose(sample_file, track='both')

    assert dual_res['status'] == 'success'
    assert dual_res['track_a'] is not None, "Track A result missing"
    assert dual_res['track_b'] is not None, "Track B result missing"
    comp = dual_res['comparison']
    print(f"  ✓ Translation Delta: {comp['translation_delta_m'] * 100:.1f} cm")
    print(f"  ✓ Angular Delta: {comp['rotation_delta_deg']}°")
    print(f"  ✓ Agreement Status: {comp['agreement_status']}")

    # -------------------------------------------------------------
    # 5. Test 3D Point Cloud Generator (WebGL payload)
    # -------------------------------------------------------------
    print("\n[5/6] Testing Interactive 3D Point Cloud Payload Generation...")
    cloud_payload = dual_res['point_cloud_3d']
    pts_count = cloud_payload['total_points']
    print(f"  ✓ Total WebGL Points: {pts_count}")
    print(f"  ✓ Bounds X: [{cloud_payload['bounds']['min_x']}, {cloud_payload['bounds']['max_x']}] m")
    print(f"  ✓ Bounds Y: [{cloud_payload['bounds']['min_y']}, {cloud_payload['bounds']['max_y']}] m")
    print(f"  ✓ Bounds Z: [{cloud_payload['bounds']['min_z']}, {cloud_payload['bounds']['max_z']}] m")
    assert pts_count > 1000 and pts_count <= 35000, f"Point count {pts_count} outside expected range"
    # Verify [x, y, z, r, g, b] structure of sample point
    sample_pt = cloud_payload['points'][0]
    assert len(sample_pt) == 6, f"Point elements must be 6, got {len(sample_pt)}"

    # -------------------------------------------------------------
    # 6. Test Flask API Endpoints with Authentication
    # -------------------------------------------------------------
    print("\n[6/6] Testing Flask API Endpoints (/api/ml/estimate-pose & /api/ml/point-cloud-3d)...")
    app = create_app('development')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    client = app.test_client()

    with app.app_context():
        db.create_all()
        # Create test user and obtain JWT token
        suffix = uuid.uuid4().hex[:6]
        user_reg = client.post('/api/auth/register', json={
            'email': f'pose_tester_{suffix}@example.com',
            'username': f'posetester_{suffix}',
            'password': 'StrongPassword123!',
            'full_name': 'Pose Test Engineer'
        })
        assert user_reg.status_code == 201, f"Registration failed: {user_reg.get_json()}"

        login_res = client.post('/api/auth/login', json={
            'email': f'pose_tester_{suffix}@example.com',
            'password': 'StrongPassword123!'
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.get_json()}"
        access_token = login_res.get_json()['access_token']
        headers = {'Authorization': f'Bearer {access_token}'}

        # Test POST /api/ml/estimate-pose
        res_api_pose = client.post('/api/ml/estimate-pose', json={
            'filename': 'sample_rgbd_box.png',
            'track': 'both'
        }, headers=headers)
        assert res_api_pose.status_code == 200, f"Pose API failed: {res_api_pose.get_json()}"
        pose_data = res_api_pose.get_json()['pose_result']
        assert pose_data['status'] == 'success'
        assert 'track_a' in pose_data and 'track_b' in pose_data
        print("  ✓ POST /api/ml/estimate-pose returned 200 OK with Dual-Track results!")

        # Test POST /api/ml/point-cloud-3d
        res_api_cloud = client.post('/api/ml/point-cloud-3d', json={
            'filename': 'sample_rgbd_box.png',
            'max_points': 20000
        }, headers=headers)
        assert res_api_cloud.status_code == 200, f"Point cloud API failed: {res_api_cloud.get_json()}"
        cloud_data = res_api_cloud.get_json()['point_cloud']
        assert cloud_data['total_points'] > 0
        print(f"  ✓ POST /api/ml/point-cloud-3d returned 200 OK with {cloud_data['total_points']} 3D points!")

    print("\n" + "=" * 65)
    print("🎉 ALL 6 POSE BACKEND VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == '__main__':
    run_tests()
