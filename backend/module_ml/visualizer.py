"""
Module ML — Result Visualizer
Generates annotated images, confidence charts, and training metrics.
"""
import os
import io
import json
import base64
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class Visualizer:
    """Generates visual outputs for ML results."""

    # Color palette for bounding boxes and labels
    COLORS = [
        (59, 130, 246), (16, 185, 129), (245, 158, 11),
        (239, 68, 68), (139, 92, 246), (6, 182, 212),
        (236, 72, 153), (34, 197, 94), (249, 115, 22),
        (168, 85, 247),
    ]

    def __init__(self, output_dir=None):
        self.output_dir = output_dir
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    def annotate_image(self, image_path, predictions, max_display=5):
        """
        Create an annotated result image with prediction labels overlaid.
        Returns base64-encoded PNG.
        """
        img = Image.open(image_path).convert('RGB')
        draw = ImageDraw.Draw(img)
        w, h = img.size

        # Draw prediction labels on the image
        y_offset = 10
        bar_height = 28
        padding = 8

        for i, pred in enumerate(predictions[:max_display]):
            color = self.COLORS[i % len(self.COLORS)]
            confidence = pred.get('confidence_pct', pred.get('confidence', 0) * 100)
            label = f"{pred['class_name']} ({confidence:.1f}%)"

            # Draw background rectangle
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            except Exception:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            bar_w = min(int((confidence / 100) * (w - 20)), w - 20)

            # Background bar
            draw.rectangle(
                [10, y_offset, 10 + max(bar_w, text_w + padding * 2), y_offset + bar_height],
                fill=(*color, 180),
            )

            # Text
            draw.text((10 + padding, y_offset + 4), label, fill=(255, 255, 255), font=font)

            y_offset += bar_height + 4

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def generate_confidence_chart_data(self, predictions):
        """Generate data for a confidence bar chart (rendered by frontend)."""
        return {
            'labels': [p['class_name'] for p in predictions],
            'values': [p.get('confidence_pct', p.get('confidence', 0) * 100) for p in predictions],
            'colors': [
                f'rgb({c[0]}, {c[1]}, {c[2]})'
                for c in self.COLORS[:len(predictions)]
            ],
        }

    def generate_training_chart_data(self, history):
        """Generate training metrics chart data for the frontend."""
        if not history:
            return None

        epochs = list(range(1, len(history.get('loss', [])) + 1))

        return {
            'epochs': epochs,
            'loss': {
                'train': history.get('loss', []),
                'val': history.get('val_loss', []),
            },
            'accuracy': {
                'train': history.get('accuracy', []),
                'val': history.get('val_accuracy', []),
            },
        }

    def create_comparison_grid(self, query_image_path, matched_image_paths, predictions):
        """
        Create a grid image showing the query image alongside top matches.
        Returns base64-encoded PNG.
        """
        cell_size = 200
        padding = 10
        num_matches = min(len(matched_image_paths), 4)
        grid_w = cell_size * (num_matches + 1) + padding * (num_matches + 2)
        grid_h = cell_size + padding * 2 + 40  # extra for labels

        grid = Image.new('RGB', (grid_w, grid_h), (13, 15, 20))
        draw = ImageDraw.Draw(grid)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except Exception:
            font = ImageFont.load_default()

        # Draw query image
        query_img = Image.open(query_image_path).convert('RGB')
        query_img = query_img.resize((cell_size, cell_size), Image.LANCZOS)
        grid.paste(query_img, (padding, padding))
        draw.text((padding, padding + cell_size + 5), "Query Image", fill=(255, 255, 255), font=font)

        # Draw matched images
        for i in range(num_matches):
            if i >= len(matched_image_paths) or not os.path.exists(matched_image_paths[i]):
                continue

            x_offset = padding + (i + 1) * (cell_size + padding)
            match_img = Image.open(matched_image_paths[i]).convert('RGB')
            match_img = match_img.resize((cell_size, cell_size), Image.LANCZOS)
            grid.paste(match_img, (x_offset, padding))

            conf = predictions[i].get('confidence_pct', 0) if i < len(predictions) else 0
            label = f"{predictions[i].get('class_name', '?')} ({conf:.1f}%)" if i < len(predictions) else ""
            draw.text((x_offset, padding + cell_size + 5), label, fill=(255, 255, 255), font=font)

        buffer = io.BytesIO()
        grid.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
