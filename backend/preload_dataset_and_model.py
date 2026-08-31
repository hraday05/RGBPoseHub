"""
RGB-Pose Hub — Dataset & Model Preloader
Downloads all CLUBS dataset object images from GitHub, runs cleaning,
preprocessing (224x224 resize, normalization, 5x augmentation),
and prepares the ML classification engine.
"""
import os
import json
import sys
from app import create_app
from module_data.dataset_loader import DatasetLoader
from module_data.data_cleaner import DataCleaner
from module_data.preprocessor import Preprocessor
from module_ml.model_trainer import ModelTrainer

def main():
    print("=" * 60)
    print("📦 RGB-Pose Hub — CLUBS Dataset & ML Model Preloader")
    print("=" * 60)

    app = create_app('development')
    dataset_dir = app.config['DATASET_FOLDER']
    model_dir = app.config['MODEL_FOLDER']

    os.makedirs(dataset_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    # Step 1: Download CLUBS Dataset
    print("\n[Step 1/4] Downloading CLUBS Dataset from GitHub...")
    loader = DatasetLoader(dataset_dir)
    meta = loader.download_all()
    print(f"  ✓ Total Remote Files Found: {meta.get('total_files', 0)}")
    print(f"  ✓ Downloaded/Local Images: {meta.get('downloaded', 0)}")

    local_images = loader.get_local_images()
    print(f"  ✓ Loaded {len(local_images)} object images locally into dataset/images/")

    # Step 2: Run Data Cleaner
    print("\n[Step 2/4] Running Data Cleaner & Integrity Verification...")
    cleaner = DataCleaner(os.path.join(dataset_dir, 'images'))
    clean_report = cleaner.clean_dataset()
    print(f"  ✓ Scanned: {clean_report['total_scanned']} images")
    print(f"  ✓ Valid: {clean_report['valid']}")
    print(f"  ✓ Duplicates: {clean_report['duplicates']}")

    # Step 3: Run Preprocessing & Augmentation
    print("\n[Step 3/4] Running Image Preprocessor & 5x Data Augmentation...")
    images_dir = os.path.join(dataset_dir, 'images')
    output_dir = os.path.join(dataset_dir, 'preprocessed')
    preprocessor = Preprocessor(images_dir, output_dir)
    prep_results = preprocessor.preprocess_dataset(augmentation_factor=5)
    print(f"  ✓ Original Processed: {prep_results.get('total_processed', 0)}")
    print(f"  ✓ Augmented Generated: {prep_results.get('total_augmented', 0)}")
    print(f"  ✓ Number of Object Classes: {len(prep_results.get('classes', {}))}")

    # Step 4: Build Model, Train & Save Metadata
    print("\n[Step 4/4] Initializing & Training ML Model Engine...")
    X_train, X_val, y_train, y_val, class_names = preprocessor.prepare_training_data()

    if X_train is not None and len(X_train) > 0:
        num_classes = len(set(y_train.tolist() + y_val.tolist()))
        print(f"  ✓ Training samples: {len(X_train)} | Validation samples: {len(X_val)}")
        print(f"  ✓ Number of target classes: {num_classes}")

        trainer = ModelTrainer(model_dir, num_classes=num_classes)
        trainer.class_names = class_names
        trainer.build_model(num_classes=num_classes)

        train_res = trainer.train(X_train, X_val, y_train, y_val, epochs=15, batch_size=16)
        print(f"  ✓ Training status: {train_res.get('status')}")
        print(f"  ✓ Epochs completed: {train_res.get('epochs', 0)}")
        print(f"  ✓ Final Training Accuracy: {train_res.get('final_accuracy', 0)*100:.2f}%")
        print(f"  ✓ Final Validation Accuracy: {train_res.get('final_val_accuracy', 0)*100:.2f}%")
    else:
        print("  ⚠ Warning: No training data found for model training.")
        trainer = ModelTrainer(model_dir, num_classes=len(prep_results.get('classes', {})))
        trainer.class_names = prep_results.get('classes', {})
        trainer.build_model(num_classes=len(prep_results.get('classes', {})))
        trainer.save_model()

    print("\n" + "=" * 60)
    print("🎉 CLUBS DATASET & ML MODEL TRAINING COMPLETE!")
    print(f"   Dataset Location: {dataset_dir}")
    print(f"   Model Location:   {model_dir}")
    print("=" * 60)

if __name__ == '__main__':
    main()
