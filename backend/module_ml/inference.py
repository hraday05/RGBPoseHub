"""
Module ML — Inference Engine
Single-image and batch prediction with confidence scores.
"""
import os
import json
import numpy as np
from PIL import Image


class InferenceEngine:
    """Handles object classification inference on uploaded images."""

    TARGET_SIZE = (224, 224)

    def __init__(self, model_dir, dataset_dir):
        self.model_dir = model_dir
        self.dataset_dir = dataset_dir
        self.model = None
        self.class_names = {}
        self._load_class_names()

    def _load_class_names(self):
        """Load class name mapping."""
        # Try from model dir first
        for search_dir in [self.model_dir,
                           os.path.join(self.dataset_dir, 'preprocessed')]:
            classes_path = os.path.join(search_dir, 'class_names.json')
            if not os.path.exists(classes_path):
                classes_path = os.path.join(search_dir, 'class_mapping.json')
            if os.path.exists(classes_path):
                with open(classes_path) as f:
                    self.class_names = json.load(f)
                return

        # Fallback: build from dataset images
        images_dir = os.path.join(self.dataset_dir, 'images')
        if os.path.exists(images_dir):
            for fname in sorted(os.listdir(images_dir)):
                if fname.endswith('.png'):
                    obj_id = fname.split('_')[0]
                    obj_name = fname.replace('.png', '').split('_', 1)[-1].replace('_', ' ').title()
                    self.class_names[obj_id] = obj_name

    def load_model(self):
        """Load the trained model for inference."""
        # Try PyTorch first
        pt_path = os.path.join(self.model_dir, 'clubs_classifier.pt')
        if os.path.exists(pt_path):
            try:
                import torch
                from torchvision import models
                checkpoint = torch.load(pt_path, map_location='cpu')
                num_classes = checkpoint.get('num_classes', 85)

                try:
                    model = models.mobilenet_v3_small(weights=None)
                except Exception:
                    model = models.mobilenet_v3_small(pretrained=False)

                in_features = model.classifier[0].in_features
                model.classifier = torch.nn.Sequential(
                    torch.nn.Linear(in_features, 256),
                    torch.nn.Hardswish(),
                    torch.nn.Dropout(p=0.2),
                    torch.nn.Linear(256, num_classes)
                )
                model.load_state_dict(checkpoint['state_dict'])
                model.eval()
                self.model = model
                self.backend = 'pytorch'
                self.inv_label_map = checkpoint.get('inv_label_map')
                return {'status': 'loaded', 'backend': 'pytorch'}
            except Exception as e:
                print(f"[InferenceEngine] Failed to load PyTorch model: {e}")

        # Fallback to TensorFlow
        try:
            import tensorflow as tf
            model_path = os.path.join(self.model_dir, 'clubs_classifier.keras')
            if os.path.exists(model_path):
                self.model = tf.keras.models.load_model(model_path)
                self.backend = 'tensorflow'
                return {'status': 'loaded', 'backend': 'tensorflow'}
        except Exception as e:
            print(f"[InferenceEngine] Failed to load TensorFlow model: {e}")

        return {'status': 'no_model', 'message': 'No trained model found'}

    def preprocess_image(self, image_path):
        """Preprocess a single image for inference."""
        img = Image.open(image_path).convert('RGB')
        img = img.resize(self.TARGET_SIZE, Image.LANCZOS)
        arr = np.array(img).astype(np.float32) / 255.0
        return np.expand_dims(arr, axis=0), img

    def predict(self, image_path, top_k=5):
        """
        Run inference on a single image.
        Returns top-K predictions with confidence scores.
        Falls back to similarity-based matching if no trained model.
        """
        if self.model is not None:
            return self._predict_with_model(image_path, top_k)
        else:
            return self._predict_similarity(image_path, top_k)

    def _predict_with_model(self, image_path, top_k=5):
        """Predict using the trained CNN model."""
        try:
            if getattr(self, 'backend', 'pytorch') == 'pytorch':
                import torch
                img = Image.open(image_path).convert('RGB')
                img = img.resize(self.TARGET_SIZE, Image.LANCZOS)
                arr = np.array(img).astype(np.float32) / 255.0
                tensor = torch.tensor(arr, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)

                with torch.no_grad():
                    outputs = self.model(tensor)
                    probabilities = torch.softmax(outputs, dim=1)[0].numpy()

                top_indices = np.argsort(probabilities)[::-1][:top_k]

                results = []
                inv_map = getattr(self, 'inv_label_map', None)
                for idx in top_indices:
                    orig_class_idx = inv_map.get(idx, idx) if inv_map else idx
                    class_id = str(orig_class_idx).zfill(3)
                    results.append({
                        'class_id': class_id,
                        'class_name': self.class_names.get(class_id,
                                      self.class_names.get(str(orig_class_idx), f'Object {orig_class_idx}')),
                        'confidence': float(probabilities[idx]),
                        'confidence_pct': round(float(probabilities[idx]) * 100, 2),
                    })

                return {
                    'status': 'success',
                    'method': 'cnn_classifier',
                    'backend': 'pytorch',
                    'predictions': results,
                    'total_classes': len(probabilities),
                }

            else:
                input_tensor, _ = self.preprocess_image(image_path)
                predictions = self.model.predict(input_tensor, verbose=0)[0]

                top_indices = np.argsort(predictions)[::-1][:top_k]

                results = []
                for idx in top_indices:
                    class_id = str(idx).zfill(3)
                    results.append({
                        'class_id': class_id,
                        'class_name': self.class_names.get(class_id,
                                      self.class_names.get(str(idx), f'Object {idx}')),
                        'confidence': float(predictions[idx]),
                        'confidence_pct': round(float(predictions[idx]) * 100, 2),
                    })

                return {
                    'status': 'success',
                    'method': 'cnn_classifier',
                    'backend': 'tensorflow',
                    'predictions': results,
                    'total_classes': len(predictions),
                }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}

    def _predict_similarity(self, image_path, top_k=5):
        """
        Fallback: pixel-level similarity comparison against dataset.
        Used when no trained model is available.
        """
        try:
            query_img = Image.open(image_path).convert('RGB')
            query_img = query_img.resize(self.TARGET_SIZE, Image.LANCZOS)
            query_arr = np.array(query_img).astype(np.float32).flatten()
            query_norm = np.linalg.norm(query_arr)

            images_dir = os.path.join(self.dataset_dir, 'images')
            if not os.path.exists(images_dir):
                return {'status': 'error', 'message': 'Dataset not downloaded'}

            similarities = []
            for fname in sorted(os.listdir(images_dir)):
                if not fname.endswith('.png'):
                    continue
                fpath = os.path.join(images_dir, fname)
                try:
                    ref_img = Image.open(fpath).convert('RGB')
                    ref_img = ref_img.resize(self.TARGET_SIZE, Image.LANCZOS)
                    ref_arr = np.array(ref_img).astype(np.float32).flatten()
                    ref_norm = np.linalg.norm(ref_arr)

                    # Cosine similarity
                    if query_norm > 0 and ref_norm > 0:
                        sim = float(np.dot(query_arr, ref_arr) / (query_norm * ref_norm))
                    else:
                        sim = 0.0

                    obj_id = fname.split('_')[0]
                    obj_name = fname.replace('.png', '').split('_', 1)[-1].replace('_', ' ').title()
                    similarities.append({
                        'class_id': obj_id,
                        'class_name': obj_name,
                        'confidence': sim,
                        'confidence_pct': round(sim * 100, 2),
                        'filename': fname,
                    })
                except Exception:
                    pass

            # Sort by similarity
            similarities.sort(key=lambda x: x['confidence'], reverse=True)

            return {
                'status': 'success',
                'method': 'cosine_similarity',
                'predictions': similarities[:top_k],
                'total_compared': len(similarities),
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def batch_predict(self, image_paths, top_k=5):
        """Run inference on multiple images."""
        results = []
        for path in image_paths:
            result = self.predict(path, top_k)
            result['image_path'] = path
            results.append(result)
        return results
