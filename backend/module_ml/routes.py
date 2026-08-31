"""
Module ML — API Routes
Inference, training, model status, and visualization endpoints.
"""
import os
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from module_ml.model_trainer import ModelTrainer
from module_ml.inference import InferenceEngine
from module_ml.visualizer import Visualizer
from module_auth.middleware import log_activity

ml_bp = Blueprint('ml', __name__)


def _get_trainer():
    return ModelTrainer(
        model_dir=current_app.config['MODEL_FOLDER'],
    )

def _get_engine():
    return InferenceEngine(
        model_dir=current_app.config['MODEL_FOLDER'],
        dataset_dir=current_app.config['DATASET_FOLDER'],
    )

def _get_visualizer():
    return Visualizer(
        output_dir=os.path.join(current_app.config['MODEL_FOLDER'], 'visualizations')
    )


@ml_bp.route('/status', methods=['GET'])
@jwt_required()
def model_status():
    """Get current model status and info."""
    trainer = _get_trainer()
    info = trainer.get_model_info()
    history = trainer.get_training_history()

    return jsonify({
        'model': info,
        'has_training_history': history is not None,
        'training_summary': {
            'epochs': history.get('epochs_completed', 0) if history else 0,
            'final_accuracy': history['accuracy'][-1] if history and history.get('accuracy') else None,
            'final_val_accuracy': history['val_accuracy'][-1] if history and history.get('val_accuracy') else None,
        } if history else None,
    }), 200


@ml_bp.route('/build', methods=['POST'])
@jwt_required()
def build_model():
    """Build the ML model architecture."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    num_classes = data.get('num_classes', 85)

    trainer = _get_trainer()
    result = trainer.build_model(num_classes=num_classes)

    log_activity(user_id, 'model_build', 'ml',
                 f'Built model with {num_classes} classes',
                 metadata=result)

    return jsonify({'result': result}), 200


@ml_bp.route('/train', methods=['POST'])
@jwt_required()
def train_model():
    """Train the model on preprocessed dataset."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    epochs = data.get('epochs', 20)
    batch_size = data.get('batch_size', 16)

    # Load preprocessed data
    from module_data.preprocessor import Preprocessor
    images_dir = os.path.join(current_app.config['DATASET_FOLDER'], 'images')
    output_dir = os.path.join(current_app.config['DATASET_FOLDER'], 'preprocessed')
    preprocessor = Preprocessor(images_dir, output_dir)

    X_train, X_val, y_train, y_val, class_names = preprocessor.prepare_training_data()

    if X_train is None:
        return jsonify({
            'error': 'No training data available. Please preprocess the dataset first.'
        }), 400

    # Build and train
    num_classes = len(set(y_train.tolist() + y_val.tolist()))
    trainer = _get_trainer()
    trainer.class_names = class_names
    trainer.build_model(num_classes=num_classes)

    log_activity(user_id, 'training_start', 'ml',
                 f'Started training: {epochs} epochs, batch_size={batch_size}')

    result = trainer.train(X_train, X_val, y_train, y_val,
                          epochs=epochs, batch_size=batch_size)

    log_activity(user_id, 'training_complete', 'ml',
                 f'Training complete: accuracy={result.get("final_accuracy", "N/A")}',
                 metadata=result)

    return jsonify({'result': result}), 200


@ml_bp.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    """Run inference on an uploaded image."""
    user_id = get_jwt_identity()

    if 'image' not in request.files:
        # Check if filename was passed (for already-uploaded images)
        data = request.get_json() or {}
        filename = data.get('filename')
        if filename:
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        else:
            return jsonify({'error': 'No image provided'}), 400
    else:
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save temporarily
        import uuid
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
        filename = f'{uuid.uuid4().hex}.{ext}'
        image_path = os.path.join(upload_dir, filename)
        file.save(image_path)

    if not os.path.exists(image_path):
        return jsonify({'error': 'Image file not found'}), 404

    # Run inference
    engine = _get_engine()
    engine.load_model()
    top_k = request.args.get('top_k', 5, type=int)
    results = engine.predict(image_path, top_k=top_k)

    # Generate annotated image
    visualizer = _get_visualizer()
    annotated = None
    chart_data = None
    if results.get('predictions'):
        annotated = visualizer.annotate_image(image_path, results['predictions'])
        chart_data = visualizer.generate_confidence_chart_data(results['predictions'])

    # Read original image as base64
    import base64
    with open(image_path, 'rb') as f:
        original_b64 = base64.b64encode(f.read()).decode('utf-8')

    log_activity(user_id, 'image_analysis', 'ml',
                 f'Analyzed image: {filename}',
                 metadata={
                     'filename': filename,
                     'method': results.get('method'),
                     'top_prediction': results['predictions'][0]['class_name'] if results.get('predictions') else None,
                     'top_confidence': results['predictions'][0].get('confidence_pct') if results.get('predictions') else None,
                 })

    return jsonify({
        'results': results,
        'original_image': original_b64,
        'annotated_image': annotated,
        'chart_data': chart_data,
        'filename': filename,
    }), 200


@ml_bp.route('/predict-dataset/<filename>', methods=['POST'])
@jwt_required()
def predict_dataset_image(filename):
    """Run inference on a dataset image."""
    user_id = get_jwt_identity()
    images_dir = os.path.join(current_app.config['DATASET_FOLDER'], 'images')
    image_path = os.path.join(images_dir, filename)

    if not os.path.exists(image_path):
        return jsonify({'error': 'Dataset image not found'}), 404

    engine = _get_engine()
    engine.load_model()
    results = engine.predict(image_path, top_k=5)

    visualizer = _get_visualizer()
    annotated = None
    chart_data = None
    if results.get('predictions'):
        annotated = visualizer.annotate_image(image_path, results['predictions'])
        chart_data = visualizer.generate_confidence_chart_data(results['predictions'])

    import base64
    with open(image_path, 'rb') as f:
        original_b64 = base64.b64encode(f.read()).decode('utf-8')

    log_activity(user_id, 'dataset_analysis', 'ml',
                 f'Analyzed dataset image: {filename}',
                 metadata={'filename': filename, 'method': results.get('method')})

    return jsonify({
        'results': results,
        'original_image': original_b64,
        'annotated_image': annotated,
        'chart_data': chart_data,
    }), 200


@ml_bp.route('/training-history', methods=['GET'])
@jwt_required()
def training_history():
    """Get training metrics history for visualization."""
    trainer = _get_trainer()
    history = trainer.get_training_history()

    if not history:
        return jsonify({'error': 'No training history available'}), 404

    visualizer = _get_visualizer()
    chart_data = visualizer.generate_training_chart_data(history)

    return jsonify({
        'history': history,
        'chart_data': chart_data,
    }), 200
