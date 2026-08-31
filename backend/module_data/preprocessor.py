"""
Module Data — Image Preprocessor
Normalizes, augments, and prepares images for the ML pipeline.
"""
import os
import json
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import random


class Preprocessor:
    """Handles image preprocessing and augmentation for model training."""

    TARGET_SIZE = (224, 224)
    NORMALIZATION_MEAN = [0.485, 0.456, 0.406]  # ImageNet standards
    NORMALIZATION_STD = [0.229, 0.224, 0.225]

    def __init__(self, images_dir, output_dir):
        self.images_dir = images_dir
        self.output_dir = output_dir
        self.processed_dir = os.path.join(output_dir, 'processed')
        self.augmented_dir = os.path.join(output_dir, 'augmented')
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.augmented_dir, exist_ok=True)

    def resize_image(self, img, size=None):
        """Resize image to target size with aspect ratio preservation + padding."""
        if size is None:
            size = self.TARGET_SIZE

        # Resize maintaining aspect ratio
        img.thumbnail(size, Image.LANCZOS)

        # Pad to exact target size
        new_img = Image.new('RGB', size, (0, 0, 0))
        paste_x = (size[0] - img.size[0]) // 2
        paste_y = (size[1] - img.size[1]) // 2
        new_img.paste(img, (paste_x, paste_y))
        return new_img

    def normalize_array(self, img_array):
        """Normalize pixel values to [0, 1] range with ImageNet statistics."""
        arr = img_array.astype(np.float32) / 255.0
        for c in range(3):
            arr[:, :, c] = (arr[:, :, c] - self.NORMALIZATION_MEAN[c]) / self.NORMALIZATION_STD[c]
        return arr

    def augment_image(self, img, num_augmentations=5):
        """Apply random augmentations to create additional training samples."""
        augmented = []
        for i in range(num_augmentations):
            aug = img.copy()

            # Random horizontal flip
            if random.random() > 0.5:
                aug = aug.transpose(Image.FLIP_LEFT_RIGHT)

            # Random rotation (-15 to 15 degrees)
            angle = random.uniform(-15, 15)
            aug = aug.rotate(angle, fillcolor=(0, 0, 0), expand=False)

            # Random brightness adjustment
            if random.random() > 0.5:
                factor = random.uniform(0.7, 1.3)
                aug = ImageEnhance.Brightness(aug).enhance(factor)

            # Random contrast adjustment
            if random.random() > 0.5:
                factor = random.uniform(0.8, 1.2)
                aug = ImageEnhance.Contrast(aug).enhance(factor)

            # Random color jitter
            if random.random() > 0.6:
                factor = random.uniform(0.8, 1.2)
                aug = ImageEnhance.Color(aug).enhance(factor)

            # Random Gaussian blur
            if random.random() > 0.7:
                aug = aug.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

            augmented.append(aug)
        return augmented

    def preprocess_single(self, image_path):
        """Preprocess a single image: resize + normalize."""
        img = Image.open(image_path).convert('RGB')
        img = self.resize_image(img)
        arr = np.array(img)
        normalized = self.normalize_array(arr)
        return img, normalized

    def preprocess_dataset(self, augmentation_factor=5):
        """Preprocess the entire dataset with augmentation."""
        if not os.path.exists(self.images_dir):
            return {'status': 'error', 'message': 'Images directory not found'}

        results = {
            'total_original': 0,
            'total_processed': 0,
            'total_augmented': 0,
            'classes': {},
        }

        for fname in sorted(os.listdir(self.images_dir)):
            if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue

            fpath = os.path.join(self.images_dir, fname)
            obj_id = fname.split('_')[0]
            obj_name = fname.replace('.png', '').replace('.jpg', '')

            try:
                img = Image.open(fpath).convert('RGB')
                resized = self.resize_image(img)

                # Save processed image
                processed_path = os.path.join(self.processed_dir, fname)
                resized.save(processed_path)
                results['total_original'] += 1
                results['total_processed'] += 1

                # Track class
                results['classes'][obj_id] = obj_name

                # Generate augmentations
                augmented_images = self.augment_image(resized, augmentation_factor)
                for j, aug_img in enumerate(augmented_images):
                    aug_fname = f'{obj_id}_aug_{j}.png'
                    aug_path = os.path.join(self.augmented_dir, aug_fname)
                    aug_img.save(aug_path)
                    results['total_augmented'] += 1

            except Exception as e:
                print(f"[Preprocessor] Error processing {fname}: {e}")

        # Save class mapping
        class_map_path = os.path.join(self.output_dir, 'class_mapping.json')
        with open(class_map_path, 'w') as f:
            json.dump(results['classes'], f, indent=2)

        results['status'] = 'complete'
        return results

    def prepare_training_data(self):
        """Prepare train/val split arrays for model training."""
        all_images = []
        all_labels = []
        class_names = {}

        # Collect processed images
        for fname in sorted(os.listdir(self.processed_dir)):
            if not fname.endswith('.png'):
                continue
            fpath = os.path.join(self.processed_dir, fname)
            obj_id = int(fname.split('_')[0])
            class_names[obj_id] = fname.replace('.png', '').split('_', 1)[-1]

            img = Image.open(fpath).convert('RGB')
            arr = np.array(img).astype(np.float32) / 255.0
            all_images.append(arr)
            all_labels.append(obj_id)

        # Collect augmented images
        for fname in sorted(os.listdir(self.augmented_dir)):
            if not fname.endswith('.png'):
                continue
            fpath = os.path.join(self.augmented_dir, fname)
            obj_id = int(fname.split('_')[0])

            img = Image.open(fpath).convert('RGB')
            arr = np.array(img).astype(np.float32) / 255.0
            all_images.append(arr)
            all_labels.append(obj_id)

        if not all_images:
            return None, None, None, None, {}

        X = np.array(all_images)
        y = np.array(all_labels)

        # Shuffle
        indices = np.arange(len(X))
        np.random.shuffle(indices)
        X = X[indices]
        y = y[indices]

        # 80/20 split
        split_idx = int(0.8 * len(X))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        return X_train, X_val, y_train, y_val, class_names
