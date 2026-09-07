"""
RGB-D Data Utilities
Handles loading, parsing, depth scaling, camera intrinsic calibration,
and 3D pinhole unprojection for RGB-D frames.
"""

import os
import cv2
import numpy as np
from PIL import Image


def get_default_camera_matrix(width=640, height=480, fx=615.0, fy=615.0, cx=None, cy=None):
    """
    Returns 3x3 camera intrinsic matrix K.
    Defaults to CLUBS RealSense/PrimeSense sensor parameters.
    """
    if cx is None:
        cx = width / 2.0
    if cy is None:
        cy = height / 2.0

    K = np.array([
        [fx, 0.0, cx],
        [0.0, fy, cy],
        [0.0, 0.0, 1.0]
    ], dtype=np.float32)
    return K


def load_rgbd(rgb_or_rgba_path, depth_path=None):
    """
    Loads RGB and metric Depth array from either:
    1. A single 4-channel RGBA image (where Alpha encodes depth).
    2. A pair of RGB image and Depth map image.

    Returns:
        rgb (np.ndarray): (H, W, 3) uint8 RGB array
        depth_m (np.ndarray): (H, W) float32 metric depth array in meters
        info (dict): Summary metadata (min_depth, max_depth, mean_depth, format)
    """
    if not os.path.exists(rgb_or_rgba_path):
        raise FileNotFoundError(f"Image not found at {rgb_or_rgba_path}")

    img_pil = Image.open(rgb_or_rgba_path)
    img_mode = img_pil.mode

    # Case 1: Separate depth file provided
    if depth_path and os.path.exists(depth_path):
        rgb = np.array(img_pil.convert('RGB'), dtype=np.uint8)
        
        # Check depth format (16-bit millimeter or 8-bit normalized)
        depth_raw = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
        if depth_raw is None:
            depth_pil = Image.open(depth_path)
            depth_raw = np.array(depth_pil)

        if depth_raw.dtype == np.uint16:
            # 16-bit depth sensor (mm -> meters)
            depth_m = depth_raw.astype(np.float32) / 1000.0
            depth_format = "16-bit raw sensor (mm)"
        else:
            # 8-bit normalized depth map (scaled 0-255 -> 0.3m to 2.5m)
            depth_raw = depth_raw.astype(np.float32)
            if len(depth_raw.shape) == 3:
                depth_raw = depth_raw[:, :, 0]
            depth_m = 0.3 + (depth_raw / 255.0) * 2.2
            depth_format = "8-bit normalized (0.3m - 2.5m)"

    # Case 2: Single 4-Channel RGBA image (Depth in Alpha)
    elif img_mode == 'RGBA':
        rgba_arr = np.array(img_pil)
        rgb = rgba_arr[:, :, :3]
        alpha = rgba_arr[:, :, 3].astype(np.float32)
        # In our generator & CLUBS demo, alpha channel encodes depth (0.3m - 2.5m)
        depth_m = 0.3 + (alpha / 255.0) * 2.2
        depth_format = "4-channel RGBA (Alpha channel depth)"

    # Case 3: Single 3-channel RGB image (Depth synthesized via depth estimation heuristic)
    else:
        rgb = np.array(img_pil.convert('RGB'), dtype=np.uint8)
        h, w = rgb.shape[:2]
        # Slanted ground plane + center depth fallback
        y_grid, x_grid = np.indices((h, w), dtype=np.float32)
        depth_m = 1.4 - (y_grid / h) * 0.5  # 0.9m to 1.4m
        depth_format = "Monocular depth approximation"

    # Make sure dimensions match
    if rgb.shape[:2] != depth_m.shape[:2]:
        depth_m = cv2.resize(depth_m, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)

    valid_mask = (depth_m > 0.1) & (depth_m < 5.0)
    valid_depths = depth_m[valid_mask]

    info = {
        'format': depth_format,
        'width': int(rgb.shape[1]),
        'height': int(rgb.shape[0]),
        'valid_pixels_pct': float(np.mean(valid_mask) * 100.0),
        'min_depth_m': float(np.min(valid_depths)) if len(valid_depths) > 0 else 0.5,
        'max_depth_m': float(np.max(valid_depths)) if len(valid_depths) > 0 else 2.5,
        'mean_depth_m': float(np.mean(valid_depths)) if len(valid_depths) > 0 else 1.0,
    }

    return rgb, depth_m, info


def unproject_depth_to_points(depth_m, rgb=None, K=None, depth_min=0.2, depth_max=4.0, stride=2):
    """
    Unprojects 2D depth map (u, v, Z) into 3D camera coordinates (X, Y, Z).
    
    Formula:
        X = (u - cx) * Z / fx
        Y = (v - cy) * Z / fy
        Z = Z
    
    Returns:
        points_3d: (N, 3) float32 coordinates in meters
        colors: (N, 3) float32 RGB colors in range [0, 1]
    """
    h, w = depth_m.shape
    if K is None:
        K = get_default_camera_matrix(width=w, height=h)

    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]

    # Grid of pixel coordinates subsampled by stride
    v_indices = np.arange(0, h, stride)
    u_indices = np.arange(0, w, stride)
    u_grid, v_grid = np.meshgrid(u_indices, v_indices)

    # Subsampled depth and colors
    z_sub = depth_m[::stride, ::stride]
    
    mask = (z_sub >= depth_min) & (z_sub <= depth_max) & ~np.isnan(z_sub)

    u_valid = u_grid[mask]
    v_valid = v_grid[mask]
    z_valid = z_sub[mask]

    # Unproject
    x_valid = (u_valid - cx) * z_valid / fx
    y_valid = (v_valid - cy) * z_valid / fy

    points_3d = np.column_stack([x_valid, y_valid, z_valid]).astype(np.float32)

    if rgb is not None:
        rgb_sub = rgb[::stride, ::stride, :]
        colors = (rgb_sub[mask] / 255.0).astype(np.float32)
    else:
        colors = np.ones_like(points_3d, dtype=np.float32)

    return points_3d, colors


def create_point_cloud_payload(rgb, depth_m, K=None, max_points=35000, object_bbox=None):
    """
    Generates a downsampled point cloud payload formatted for WebGL / Three.js.
    Returns:
        dict with:
          - 'points': list of [x, y, z, r, g, b]
          - 'total_points': int
          - 'bounds': {min_x, max_x, min_y, max_y, min_z, max_z}
          - 'camera_intrinsics': {fx, fy, cx, cy}
    """
    h, w = depth_m.shape
    if K is None:
        K = get_default_camera_matrix(width=w, height=h)

    # Calculate stride so total points <= max_points
    total_pixels = h * w
    stride = max(2, int(np.ceil(np.sqrt(total_pixels / max_points))))

    points_3d, colors = unproject_depth_to_points(depth_m, rgb=rgb, K=K, stride=stride)

    if len(points_3d) == 0:
        return {
            'points': [],
            'total_points': 0,
            'bounds': {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0, 'min_z': 0, 'max_z': 0},
            'camera_intrinsics': {'fx': float(K[0,0]), 'fy': float(K[1,1]), 'cx': float(K[0,2]), 'cy': float(K[1,2])}
        }

    # Interleave [x, y, z, r, g, b] rounded for compact JSON transfer
    x = np.round(points_3d[:, 0], 4)
    y = np.round(points_3d[:, 1], 4)
    z = np.round(points_3d[:, 2], 4)
    r = np.round(colors[:, 0], 3)
    g = np.round(colors[:, 1], 3)
    b = np.round(colors[:, 2], 3)

    combined = np.column_stack([x, y, z, r, g, b]).tolist()

    return {
        'points': combined,
        'total_points': len(combined),
        'stride_used': stride,
        'bounds': {
            'min_x': float(np.min(x)),
            'max_x': float(np.max(x)),
            'min_y': float(np.min(y)),
            'max_y': float(np.max(y)),
            'min_z': float(np.min(z)),
            'max_z': float(np.max(z)),
        },
        'camera_intrinsics': {
            'fx': float(K[0, 0]),
            'fy': float(K[1, 1]),
            'cx': float(K[0, 2]),
            'cy': float(K[1, 2]),
        }
    }
