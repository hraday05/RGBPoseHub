"""
Module ML — Model Trainer
PyTorch MobileNetV3 transfer learning for CLUBS object classification.
"""
import os
import json
import numpy as np
from datetime import datetime


class ModelTrainer:
    """
    CNN-based object classifier using MobileNetV3 transfer learning in PyTorch.
    Designed for the CLUBS dataset (~85 object classes).
    """

    def __init__(self, model_dir, num_classes=85):
        self.model_dir = model_dir
        self.num_classes = num_classes
        self.model = None
        self.backend = None  # 'pytorch' or 'tensorflow'
        self.history = None
        self.class_names = {}
        self.training_log = []
        os.makedirs(model_dir, exist_ok=True)

    def build_model(self, num_classes=None):
        """Build MobileNetV3-based classification model using PyTorch."""
        if num_classes:
            self.num_classes = num_classes

        try:
            import torch
            import torch.nn as nn
            from torchvision import models

            # Load pretrained MobileNetV3 Small
            try:
                base_model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
            except Exception:
                base_model = models.mobilenet_v3_small(pretrained=True)

            # Replace classifier head for self.num_classes
            in_features = base_model.classifier[0].in_features
            base_model.classifier = nn.Sequential(
                nn.Linear(in_features, 256),
                nn.Hardswish(),
                nn.Dropout(p=0.2),
                nn.Linear(256, self.num_classes)
            )

            self.model = base_model
            self.backend = 'pytorch'

            total_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

            return {
                'status': 'built',
                'backend': 'pytorch',
                'total_params': total_params,
                'trainable_params': trainable_params,
                'num_classes': self.num_classes,
            }
        except ImportError:
            return self._build_tf_or_simple_model(num_classes)

    def _build_tf_or_simple_model(self, num_classes=None):
        """Fallback to TensorFlow or simple mode."""
        try:
            import tensorflow as tf
            from tensorflow.keras.applications import MobileNetV2
            from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout, BatchNormalization
            from tensorflow.keras.models import Model

            base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
            base_model.trainable = False
            x = GlobalAveragePooling2D()(base_model.output)
            x = BatchNormalization()(x)
            x = Dense(256, activation='relu')(x)
            x = Dropout(0.3)(x)
            predictions = Dense(self.num_classes, activation='softmax')(x)

            self.model = Model(inputs=base_model.input, outputs=predictions)
            self.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                               loss='sparse_categorical_crossentropy', metrics=['accuracy'])
            self.backend = 'tensorflow'

            return {
                'status': 'built',
                'backend': 'tensorflow',
                'num_classes': self.num_classes,
            }
        except Exception:
            self.model = None
            self.backend = 'simple'
            return {'status': 'built_simple', 'num_classes': self.num_classes}

    def train(self, X_train, X_val, y_train, y_val, epochs=15, batch_size=16):
        """Train the model on preprocessed data."""
        if self.model is None:
            self.build_model()

        if self.backend == 'pytorch':
            return self._train_pytorch(X_train, X_val, y_train, y_val, epochs, batch_size)
        elif self.backend == 'tensorflow':
            return self._train_tensorflow(X_train, X_val, y_train, y_val, epochs, batch_size)
        else:
            return {'status': 'error', 'message': 'No ML backend available for training.'}

    def _train_pytorch(self, X_train, X_val, y_train, y_val, epochs=15, batch_size=16):
        """Train PyTorch model."""
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import TensorDataset, DataLoader

            # Map labels to 0..N-1 range if needed
            unique_labels = sorted(list(set(y_train.tolist() + y_val.tolist())))
            label_map = {orig: i for i, orig in enumerate(unique_labels)}
            y_train_mapped = np.array([label_map[y] for y in y_train])
            y_val_mapped = np.array([label_map[y] for y in y_val])

            # Store label map for inference
            self.label_map = label_map
            self.inv_label_map = {i: orig for orig, i in label_map.items()}

            # Convert (N, H, W, C) to (N, C, H, W) PyTorch Tensors
            X_tr_t = torch.tensor(X_train, dtype=torch.float32).permute(0, 3, 1, 2)
            y_tr_t = torch.tensor(y_train_mapped, dtype=torch.long)

            X_va_t = torch.tensor(X_val, dtype=torch.float32).permute(0, 3, 1, 2)
            y_va_t = torch.tensor(y_val_mapped, dtype=torch.long)

            train_ds = TensorDataset(X_tr_t, y_tr_t)
            val_ds = TensorDataset(X_va_t, y_va_t)

            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
            val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

            device = torch.device('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
            self.model.to(device)

            criterion = nn.CrossEntropyLoss()
            optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)

            history = {'loss': [], 'accuracy': [], 'val_loss': [], 'val_accuracy': []}
            best_val_loss = float('inf')
            patience_counter = 0

            print(f"[ModelTrainer] Training PyTorch MobileNetV3 on device: {device}")
            for epoch in range(epochs):
                # Train phase
                self.model.train()
                train_loss, train_correct, train_total = 0.0, 0, 0
                for images, labels in train_loader:
                    images, labels = images.to(device), labels.to(device)
                    optimizer.zero_grad()
                    outputs = self.model(images)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()

                    train_loss += loss.item() * images.size(0)
                    _, preds = torch.max(outputs, 1)
                    train_correct += (preds == labels).sum().item()
                    train_total += images.size(0)

                epoch_loss = train_loss / max(1, train_total)
                epoch_acc = train_correct / max(1, train_total)

                # Validation phase
                self.model.eval()
                val_loss, val_correct, val_total = 0.0, 0, 0
                with torch.no_grad():
                    for images, labels in val_loader:
                        images, labels = images.to(device), labels.to(device)
                        outputs = self.model(images)
                        loss = criterion(outputs, labels)

                        val_loss += loss.item() * images.size(0)
                        _, preds = torch.max(outputs, 1)
                        val_correct += (preds == labels).sum().item()
                        val_total += images.size(0)

                epoch_val_loss = val_loss / max(1, val_total)
                epoch_val_acc = val_correct / max(1, val_total)

                history['loss'].append(round(float(epoch_loss), 4))
                history['accuracy'].append(round(float(epoch_acc), 4))
                history['val_loss'].append(round(float(epoch_val_loss), 4))
                history['val_accuracy'].append(round(float(epoch_val_acc), 4))

                scheduler.step(epoch_val_loss)

                print(f"Epoch [{epoch+1}/{epochs}] — Loss: {epoch_loss:.4f}, Acc: {epoch_acc:.4f} | Val Loss: {epoch_val_loss:.4f}, Val Acc: {epoch_val_acc:.4f}")

                # Early stopping
                if epoch_val_loss < best_val_loss:
                    best_val_loss = epoch_val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= 5:
                        print(f"Early stopping triggered at epoch {epoch+1}")
                        break

            history['epochs_completed'] = len(history['loss'])
            self.history = history
            self.save_model()

            return {
                'status': 'complete',
                'backend': 'pytorch',
                'epochs': history['epochs_completed'],
                'final_accuracy': history['accuracy'][-1],
                'final_val_accuracy': history['val_accuracy'][-1],
                'final_loss': history['loss'][-1],
                'final_val_loss': history['val_loss'][-1],
                'history': history,
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}

    def _train_tensorflow(self, X_train, X_val, y_train, y_val, epochs=15, batch_size=16):
        """Train TensorFlow model fallback."""
        try:
            import tensorflow as tf
            callbacks = [
                tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
            ]
            history = self.model.fit(X_train, y_train, validation_data=(X_val, y_val),
                                     epochs=epochs, batch_size=batch_size, callbacks=callbacks, verbose=1)
            self.history = {
                'loss': [float(v) for v in history.history['loss']],
                'accuracy': [float(v) for v in history.history['accuracy']],
                'val_loss': [float(v) for v in history.history['val_loss']],
                'val_accuracy': [float(v) for v in history.history['val_accuracy']],
                'epochs_completed': len(history.history['loss']),
            }
            self.save_model()
            return {'status': 'complete', 'backend': 'tensorflow', 'history': self.history}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def save_model(self):
        """Save model weights and training history."""
        try:
            if self.model and self.backend == 'pytorch':
                import torch
                model_path = os.path.join(self.model_dir, 'clubs_classifier.pt')
                torch.save({
                    'state_dict': self.model.state_dict(),
                    'num_classes': self.num_classes,
                    'class_names': self.class_names,
                    'inv_label_map': getattr(self, 'inv_label_map', None),
                }, model_path)
                # Create dummy .keras file for legacy status checks
                keras_compat_path = os.path.join(self.model_dir, 'clubs_classifier.keras')
                with open(keras_compat_path, 'w') as f:
                    f.write("pytorch_model_placeholder")

            elif self.model and self.backend == 'tensorflow':
                model_path = os.path.join(self.model_dir, 'clubs_classifier.keras')
                self.model.save(model_path)

            if self.history:
                history_path = os.path.join(self.model_dir, 'training_history.json')
                with open(history_path, 'w') as f:
                    json.dump(self.history, f, indent=2)

            if self.class_names:
                classes_path = os.path.join(self.model_dir, 'class_names.json')
                with open(classes_path, 'w') as f:
                    json.dump(self.class_names, f, indent=2)

            return True
        except Exception as e:
            print(f"[ModelTrainer] Save error: {e}")
            return False

    def load_model(self):
        """Load a previously saved model."""
        try:
            pt_path = os.path.join(self.model_dir, 'clubs_classifier.pt')
            if os.path.exists(pt_path):
                import torch
                from torchvision import models
                checkpoint = torch.load(pt_path, map_location='cpu')
                num_classes = checkpoint.get('num_classes', self.num_classes)

                try:
                    self.model = models.mobilenet_v3_small(weights=None)
                except Exception:
                    self.model = models.mobilenet_v3_small(pretrained=False)

                in_features = self.model.classifier[0].in_features
                self.model.classifier = torch.nn.Sequential(
                    torch.nn.Linear(in_features, 256),
                    torch.nn.Hardswish(),
                    torch.nn.Dropout(p=0.2),
                    torch.nn.Linear(256, num_classes)
                )
                self.model.load_state_dict(checkpoint['state_dict'])
                self.model.eval()
                self.backend = 'pytorch'

            history_path = os.path.join(self.model_dir, 'training_history.json')
            if os.path.exists(history_path):
                with open(history_path) as f:
                    self.history = json.load(f)

            classes_path = os.path.join(self.model_dir, 'class_names.json')
            if os.path.exists(classes_path):
                with open(classes_path) as f:
                    self.class_names = json.load(f)

            return {'status': 'loaded', 'has_model': self.model is not None, 'backend': self.backend}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_training_history(self):
        """Get saved training history."""
        history_path = os.path.join(self.model_dir, 'training_history.json')
        if os.path.exists(history_path):
            with open(history_path) as f:
                return json.load(f)
        return None

    def get_model_info(self):
        """Get current model information."""
        pt_path = os.path.join(self.model_dir, 'clubs_classifier.pt')
        keras_path = os.path.join(self.model_dir, 'clubs_classifier.keras')
        model_exists = os.path.exists(pt_path) or os.path.exists(keras_path)
        active_path = pt_path if os.path.exists(pt_path) else keras_path

        return {
            'model_exists': model_exists,
            'model_loaded': self.model is not None,
            'backend': self.backend or ('pytorch' if os.path.exists(pt_path) else 'simple'),
            'num_classes': self.num_classes,
            'has_history': self.history is not None,
            'model_file_size_mb': round(os.path.getsize(active_path) / (1024 * 1024), 2)
                if os.path.exists(active_path) else 0,
        }
