"""
Sample RGB-D Image Generator for Testing & Demo
Generates 4-channel RGB-D images (RGB + Depth Map) and sample RGB + Depth image pairs
in backend/uploads/samples/ for instant testing.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def create_sample_rgbd_images(output_dir):
    os.makedirs(output_dir, exist_ok=True)

    samples = [
        {'filename': 'sample_rgbd_box.png', 'label': 'Cluttered Box Scene', 'bg_color': (30, 40, 60), 'obj_color': (220, 120, 50)},
        {'filename': 'sample_rgbd_cup.png', 'label': 'Household Mug & Bottle', 'bg_color': (20, 50, 40), 'obj_color': (50, 180, 220)},
        {'filename': 'sample_rgbd_can.png', 'label': 'Soda Can Scene', 'bg_color': (50, 20, 40), 'obj_color': (220, 50, 90)},
    ]

    generated_files = []

    for s in samples:
        w, h = 480, 360

        # Create RGB base
        img_rgb = Image.new('RGB', (w, h), color=s['bg_color'])
        draw = ImageDraw.Draw(img_rgb)

        # Draw objects
        cx, cy = w // 2, h // 2
        draw.rectangle([cx - 80, cy - 60, cx + 80, cy + 60], fill=s['obj_color'], outline=(255, 255, 255), width=3)
        draw.ellipse([cx - 120, cy - 40, cx - 60, cy + 40], fill=(240, 200, 80), outline=(255, 255, 255), width=2)
        draw.polygon([(cx + 60, cy + 60), (cx + 110, cy - 30), (cx + 130, cy + 60)], fill=(120, 220, 100))

        draw.text((20, 20), f"CLUBS Dataset Demo — {s['label']}", fill=(255, 255, 255))

        rgb_arr = np.array(img_rgb)

        # Generate realistic Depth Map Channel (0.4m to 1.8m -> scaled 20 to 240)
        x_grid, y_grid = np.meshgrid(np.arange(w), np.arange(h))
        bg_depth = 180.0 - (y_grid * 0.1)  # Slanted ground plane depth

        # Object depth masks (closer objects = lower depth values / brighter signal)
        box_mask = (x_grid >= cx - 80) & (x_grid <= cx + 80) & (y_grid >= cy - 60) & (y_grid <= cy + 60)
        cup_mask = ((x_grid - (cx - 90))**2 + (y_grid - cy)**2) <= 40**2


        depth_arr = bg_depth.copy()
        depth_arr[box_mask] = 85.0  # Box at ~0.85m depth
        depth_arr[cup_mask] = 60.0  # Cup at ~0.60m depth

        # Add Gaussian noise
        noise = np.random.normal(0, 2.0, (h, w))
        depth_arr = np.clip(depth_arr + noise, 10, 250).astype(np.uint8)

        # Stack into 4-channel RGBA (where 4th channel is Depth map)
        rgbd_arr = np.dstack([rgb_arr, depth_arr])
        img_rgbd = Image.fromarray(rgbd_arr, mode='RGBA')

        out_path = os.path.join(output_dir, s['filename'])
        img_rgbd.save(out_path, 'PNG')
        generated_files.append(out_path)

        # Also create a separate depth map file pair (sample_rgbd_box_depth.png)
        depth_pair_path = os.path.join(output_dir, s['filename'].replace('.png', '_depth.png'))
        img_depth_single = Image.fromarray(depth_arr, mode='L')
        img_depth_single.save(depth_pair_path, 'PNG')

        print(f"  ✓ Generated sample RGB-D image: {out_path}")

    return generated_files


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'uploads', 'samples')
    create_sample_rgbd_images(output_dir)
