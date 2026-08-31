"""
Module Data — API Routes
Dataset loading, cleaning, preprocessing, and browsing endpoints.
"""
import os
import base64
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from module_data.dataset_loader import DatasetLoader
from module_data.data_cleaner import DataCleaner
from module_data.preprocessor import Preprocessor
from module_auth.middleware import log_activity

data_bp = Blueprint('data', __name__)


def _get_loader():
    return DatasetLoader(current_app.config['DATASET_FOLDER'])

def _get_cleaner():
    images_dir = os.path.join(current_app.config['DATASET_FOLDER'], 'images')
    return DataCleaner(images_dir)

def _get_preprocessor():
    images_dir = os.path.join(current_app.config['DATASET_FOLDER'], 'images')
    output_dir = os.path.join(current_app.config['DATASET_FOLDER'], 'preprocessed')
    return Preprocessor(images_dir, output_dir)


@data_bp.route('/status', methods=['GET'])
@jwt_required()
def dataset_status():
    """Get current dataset status and statistics."""
    loader = _get_loader()
    stats = loader.get_dataset_stats()
    return jsonify({'dataset': stats}), 200


@data_bp.route('/download', methods=['POST'])
@jwt_required()
def download_dataset():
    """Download the CLUBS dataset from GitHub."""
    user_id = get_jwt_identity()
    loader = _get_loader()

    log_activity(user_id, 'dataset_download_start', 'data', 'Started downloading CLUBS dataset')

    results = loader.download_all()

    log_activity(user_id, 'dataset_download_complete', 'data',
                 f'Downloaded {results["downloaded"]}/{results["total_files"]} images',
                 metadata=results)

    return jsonify({
        'message': f'Downloaded {results["downloaded"]} of {results["total_files"]} images',
        'results': results,
    }), 200


@data_bp.route('/objects', methods=['GET'])
@jwt_required()
def list_objects():
    """List all available dataset objects with metadata."""
    loader = _get_loader()
    images = loader.get_local_images()

    # Convert to API-friendly format with base64 thumbnails
    objects = []
    for img_info in images:
        obj = {
            'id': img_info['id'],
            'name': img_info['name'],
            'filename': img_info['filename'],
            'width': img_info['width'],
            'height': img_info['height'],
            'size_kb': round(img_info['size_bytes'] / 1024, 1),
        }
        objects.append(obj)

    return jsonify({'objects': objects, 'total': len(objects)}), 200


@data_bp.route('/objects/<filename>/image', methods=['GET'])
@jwt_required()
def get_object_image(filename):
    """Serve a dataset object image."""
    images_dir = os.path.join(current_app.config['DATASET_FOLDER'], 'images')
    filepath = os.path.join(images_dir, filename)

    if not os.path.exists(filepath):
        return jsonify({'error': 'Image not found'}), 404

    return send_file(filepath, mimetype='image/png')


@data_bp.route('/clean', methods=['POST'])
@jwt_required()
def clean_dataset():
    """Run data cleaning pipeline on the dataset."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    remove_invalid = data.get('remove_invalid', False)

    cleaner = _get_cleaner()
    report = cleaner.clean_dataset(remove_invalid=remove_invalid)

    log_activity(user_id, 'dataset_clean', 'data',
                 f'Cleaned dataset: {report["valid"]} valid, {report["corrupted"]} issues',
                 metadata=report)

    return jsonify({'report': report}), 200


@data_bp.route('/preprocess', methods=['POST'])
@jwt_required()
def preprocess_dataset():
    """Run preprocessing + augmentation pipeline."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    aug_factor = data.get('augmentation_factor', 5)

    preprocessor = _get_preprocessor()
    results = preprocessor.preprocess_dataset(augmentation_factor=aug_factor)

    log_activity(user_id, 'dataset_preprocess', 'data',
                 f'Preprocessed: {results.get("total_processed", 0)} images, '
                 f'{results.get("total_augmented", 0)} augmented',
                 metadata=results)

    return jsonify({'results': results}), 200


@data_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_image():
    """Upload a custom image for analysis."""
    user_id = get_jwt_identity()

    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save uploaded image
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)

    import uuid
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
    filename = f'{uuid.uuid4().hex}.{ext}'
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    # Get image info
    from PIL import Image
    img = Image.open(filepath)
    w, h = img.size

    log_activity(user_id, 'image_upload', 'data',
                 f'Uploaded image: {file.filename} ({w}x{h})',
                 metadata={'original_name': file.filename, 'saved_as': filename, 'size': f'{w}x{h}'})

    # Read as base64 for preview
    with open(filepath, 'rb') as f:
        img_base64 = base64.b64encode(f.read()).decode('utf-8')

    return jsonify({
        'message': 'Image uploaded successfully',
        'image': {
            'filename': filename,
            'original_name': file.filename,
            'width': w,
            'height': h,
            'preview': img_base64,
        }
    }), 201
