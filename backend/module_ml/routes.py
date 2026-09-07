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
from module_ml.forensic_analyzer import ForensicAnalyzer
from module_ml.pose_estimator import PoseEstimator
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


@ml_bp.route('/forensic-analyze', methods=['POST'])
@jwt_required()
def forensic_analyze():
    """
    Stage 1: Run Sherloq-inspired forensic inspection and RGB-D depth verification.
    """
    user_id = get_jwt_identity()
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)

    image_path = None
    depth_path = None
    filename = None

    # Handle image upload or filename parameter
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            import uuid
            ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
            filename = f'{uuid.uuid4().hex}.{ext}'
            image_path = os.path.join(upload_dir, filename)
            file.save(image_path)

    if not image_path and request.is_json:
        data = request.get_json() or {}
        filename = data.get('filename')
        if filename:
            # Check upload folder or dataset folder
            upload_candidate = os.path.join(upload_dir, filename)
            sample_candidate = os.path.join(upload_dir, 'samples', filename)
            dataset_candidate = os.path.join(current_app.config['DATASET_FOLDER'], 'images', filename)
            if os.path.exists(upload_candidate):
                image_path = upload_candidate
            elif os.path.exists(sample_candidate):
                image_path = sample_candidate
            elif os.path.exists(dataset_candidate):
                image_path = dataset_candidate


    if 'depth_image' in request.files:
        depth_file = request.files['depth_image']
        if depth_file.filename != '':
            import uuid
            ext = depth_file.filename.rsplit('.', 1)[-1].lower() if '.' in depth_file.filename else 'png'
            depth_filename = f'depth_{uuid.uuid4().hex}.{ext}'
            depth_path = os.path.join(upload_dir, depth_filename)
            depth_file.save(depth_path)

    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Valid image required for forensic analysis'}), 400

    # Run Sherloq Forensic Inspection & RGB-D Verification
    analyzer = ForensicAnalyzer(upload_folder=upload_dir)
    forensic_results = analyzer.analyze(image_path, depth_image_path=depth_path)

    # Read original image base64
    import base64
    with open(image_path, 'rb') as f:
        original_b64 = base64.b64encode(f.read()).decode('utf-8')

    log_activity(user_id, 'forensic_analysis', 'ml',
                 f'Ran Sherloq Forensics & RGB-D Inspection: {filename}',
                 metadata={
                     'filename': filename,
                     'is_rgbd': forensic_results.get('rgbd_gatekeeper', {}).get('is_rgbd'),
                     'status': forensic_results.get('rgbd_gatekeeper', {}).get('status'),
                 })

    return jsonify({
        'forensics': forensic_results,
        'original_image': original_b64,
        'filename': filename or os.path.basename(image_path),
    }), 200


@ml_bp.route('/estimate-pose', methods=['POST'])
@jwt_required()
def estimate_pose():
    """
    Stage 2: Run 6D Object Pose Estimation (Track A EfficientPose, Track B PnP, or both).
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    filename = data.get('filename')
    depth_filename = data.get('depth_filename')
    depth_stats = data.get('depth_stats')
    prediction_info = data.get('prediction_info')
    track = data.get('track', 'both')  # 'track_a', 'track_b', or 'both'
    camera_params = data.get('camera_params')

    if not filename:
        return jsonify({'error': 'Filename required for 6D pose estimation'}), 400

    upload_dir = current_app.config['UPLOAD_FOLDER']
    image_path = os.path.join(upload_dir, filename)
    if not os.path.exists(image_path):
        image_path = os.path.join(upload_dir, 'samples', filename)
    if not os.path.exists(image_path):
        image_path = os.path.join(current_app.config['DATASET_FOLDER'], 'images', filename)

    if not os.path.exists(image_path):
        return jsonify({'error': 'Image file not found'}), 404

    # Resolve separate depth file if provided
    depth_path = None
    if depth_filename:
        cand1 = os.path.join(upload_dir, depth_filename)
        cand2 = os.path.join(upload_dir, 'samples', depth_filename)
        if os.path.exists(cand1):
            depth_path = cand1
        elif os.path.exists(cand2):
            depth_path = cand2

    # Run inference to get object class prediction if not provided
    if not prediction_info:
        engine = _get_engine()
        engine.load_model()
        pred_res = engine.predict(image_path, top_k=1)
        if pred_res.get('predictions'):
            prediction_info = pred_res['predictions'][0]

    estimator = PoseEstimator(
        model_dir=current_app.config['MODEL_FOLDER'],
        dataset_dir=current_app.config['DATASET_FOLDER'],
    )
    pose_result = estimator.estimate_pose(
        image_path,
        depth_path=depth_path,
        depth_stats=depth_stats,
        prediction_info=prediction_info,
        track=track,
        camera_params=camera_params
    )

    log_activity(user_id, 'pose_estimation', 'ml',
                 f'Ran 6D Pose Estimation ({track}) on RGB-D image: {filename}',
                 metadata={
                     'filename': filename,
                     'track': track,
                     'object_name': pose_result.get('object_name'),
                     'confidence': pose_result.get('confidence_pct'),
                 })

    return jsonify({
        'pose_result': pose_result,
        'filename': filename,
    }), 200


@ml_bp.route('/point-cloud-3d', methods=['POST'])
@jwt_required()
def get_point_cloud_3d():
    """
    Generates interactive 3D point cloud coordinates (XYZ + RGB) for WebGL rendering.
    """
    data = request.get_json() or {}
    filename = data.get('filename')
    depth_filename = data.get('depth_filename')
    max_points = data.get('max_points', 30000)
    camera_params = data.get('camera_params')

    if not filename:
        return jsonify({'error': 'Filename required for 3D point cloud generation'}), 400

    upload_dir = current_app.config['UPLOAD_FOLDER']
    image_path = os.path.join(upload_dir, filename)
    if not os.path.exists(image_path):
        image_path = os.path.join(upload_dir, 'samples', filename)
    if not os.path.exists(image_path):
        image_path = os.path.join(current_app.config['DATASET_FOLDER'], 'images', filename)

    if not os.path.exists(image_path):
        return jsonify({'error': 'Image file not found'}), 404

    depth_path = None
    if depth_filename:
        cand1 = os.path.join(upload_dir, depth_filename)
        cand2 = os.path.join(upload_dir, 'samples', depth_filename)
        if os.path.exists(cand1):
            depth_path = cand1
        elif os.path.exists(cand2):
            depth_path = cand2

    estimator = PoseEstimator(
        model_dir=current_app.config['MODEL_FOLDER'],
        dataset_dir=current_app.config['DATASET_FOLDER'],
    )
    cloud_payload = estimator.generate_point_cloud(
        image_path,
        depth_path=depth_path,
        max_points=max_points,
        camera_params=camera_params
    )

    return jsonify({
        'point_cloud': cloud_payload,
        'filename': filename,
    }), 200


@ml_bp.route('/sample-rgbd-images', methods=['GET'])
@jwt_required()
def get_sample_rgbd_images():
    """Returns list of pre-generated sample RGB-D images for testing."""
    samples_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'samples')
    os.makedirs(samples_dir, exist_ok=True)

    # Ensure samples exist
    if not os.path.exists(os.path.join(samples_dir, 'sample_rgbd_box.png')):
        from create_sample_rgbd_images import create_sample_rgbd_images
        create_sample_rgbd_images(samples_dir)

    samples = []
    for fname in sorted(os.listdir(samples_dir)):
        if fname.endswith('.png') and not fname.endswith('_depth.png'):
            samples.append({
                'filename': fname,
                'name': fname.replace('sample_rgbd_', '').replace('.png', '').replace('_', ' ').title(),
                'type': '4-Channel RGB-D',
            })

    return jsonify({'samples': samples}), 200


