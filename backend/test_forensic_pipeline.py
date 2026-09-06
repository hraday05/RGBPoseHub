"""
Automated Test Suite for Sherloq Forensic Inspection, RGB-D Gatekeeper & 6D Pose Estimation
"""

import os
import io
import unittest
import numpy as np
from PIL import Image

from app import create_app
from module_ml.forensic_analyzer import ForensicAnalyzer
from module_ml.pose_estimator import PoseEstimator


class TestForensicPipeline(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

        self.test_dir = '/tmp/test_forensic_images'
        os.makedirs(self.test_dir, exist_ok=True)

        # Create a standard 2D RGB image (3 channels)
        self.rgb_image_path = os.path.join(self.test_dir, 'test_2d_photo.jpg')
        img_rgb = Image.new('RGB', (300, 200), color=(120, 80, 200))
        img_rgb.save(self.rgb_image_path, 'JPEG', quality=85)

        # Create a 4-channel RGB-D image (RGBA where 4th channel has depth variance)
        self.rgbd_image_path = os.path.join(self.test_dir, 'test_rgbd_scene.png')
        arr_rgb = np.full((200, 300, 3), 150, dtype=np.uint8)
        # Create synthetic depth map gradient channel
        y, x = np.ogrid[:200, :300]
        depth_channel = (x + y) % 250 + 5
        arr_rgbd = np.dstack([arr_rgb, depth_channel.astype(np.uint8)])
        img_rgbd = Image.fromarray(arr_rgbd, mode='RGBA')
        img_rgbd.save(self.rgbd_image_path, 'PNG')

    def test_forensic_analyzer_standard_2d(self):
        analyzer = ForensicAnalyzer(upload_folder=self.test_dir)
        results = analyzer.analyze(self.rgb_image_path)

        self.assertEqual(results['status'], 'success')
        self.assertIn('metadata', results)
        self.assertIn('hashes', results)
        self.assertIn('color_analysis', results)
        self.assertIn('quality_analysis', results)
        self.assertIn('ela_heatmap', results)

        # Check Gatekeeper Verdict for standard 2D image
        gatekeeper = results['rgbd_gatekeeper']
        self.assertFalse(gatekeeper['is_rgbd'])
        self.assertEqual(gatekeeper['status'], 'REJECTED_NOT_RGBD')
        self.assertIn('No depth channel', gatekeeper['reason'])

    def test_forensic_analyzer_rgbd(self):
        analyzer = ForensicAnalyzer(upload_folder=self.test_dir)
        results = analyzer.analyze(self.rgbd_image_path)

        self.assertEqual(results['status'], 'success')
        gatekeeper = results['rgbd_gatekeeper']
        self.assertTrue(gatekeeper['is_rgbd'])
        self.assertEqual(gatekeeper['status'], 'VERIFIED')
        self.assertIsNotNone(gatekeeper['depth_heatmap'])

    def test_pose_estimator(self):
        estimator = PoseEstimator()
        depth_stats = {'mean_depth': 0.95, 'min_depth': 0.4, 'max_depth': 1.5}
        pred_info = {'class_name': 'box', 'confidence_pct': 94.2}

        pose_res = estimator.estimate_pose(self.rgbd_image_path, depth_stats=depth_stats, prediction_info=pred_info)

        self.assertEqual(pose_res['status'], 'success')
        self.assertEqual(pose_res['object_name'], 'box')
        self.assertIn('translation_3d', pose_res)
        self.assertIn('rotation_euler_deg', pose_res)
        self.assertIn('rotation_quaternion', pose_res)
        self.assertIn('bounding_box_3d', pose_res)
        self.assertIsNotNone(pose_res['pose_visualization'])


if __name__ == '__main__':
    unittest.main()
