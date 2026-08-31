"""
Module Data — Data Cleaner
Validates, deduplicates, and ensures quality of dataset images.
"""
import os
import hashlib
from PIL import Image


class DataCleaner:
    """Validates and cleans dataset images before preprocessing."""

    SUPPORTED_FORMATS = {'PNG', 'JPEG', 'JPG', 'BMP', 'TIFF'}
    MIN_DIMENSION = 32
    MAX_DIMENSION = 4096

    def __init__(self, images_dir):
        self.images_dir = images_dir
        self.report = {
            'total_scanned': 0,
            'valid': 0,
            'corrupted': 0,
            'duplicates': 0,
            'removed': 0,
            'issues': [],
        }

    def validate_image(self, filepath):
        """Validate a single image file for integrity and format."""
        issues = []
        try:
            img = Image.open(filepath)
            img.verify()
            img = Image.open(filepath)  # re-open after verify

            # Check format
            if img.format and img.format.upper() not in self.SUPPORTED_FORMATS:
                issues.append(f'Unsupported format: {img.format}')

            # Check dimensions
            w, h = img.size
            if w < self.MIN_DIMENSION or h < self.MIN_DIMENSION:
                issues.append(f'Too small: {w}x{h}')
            if w > self.MAX_DIMENSION or h > self.MAX_DIMENSION:
                issues.append(f'Too large: {w}x{h}')

            # Check for fully blank images
            extrema = img.convert('L').getextrema()
            if extrema[0] == extrema[1]:
                issues.append('Blank image (uniform color)')

            return {'valid': len(issues) == 0, 'issues': issues, 'size': img.size}

        except Exception as e:
            return {'valid': False, 'issues': [f'Corrupted: {str(e)}'], 'size': None}

    def compute_hash(self, filepath):
        """Compute MD5 hash for deduplication."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def find_duplicates(self):
        """Find duplicate images by content hash."""
        hashes = {}
        duplicates = []
        for fname in os.listdir(self.images_dir):
            fpath = os.path.join(self.images_dir, fname)
            if not os.path.isfile(fpath):
                continue
            h = self.compute_hash(fpath)
            if h in hashes:
                duplicates.append({'file': fname, 'duplicate_of': hashes[h]})
            else:
                hashes[h] = fname
        return duplicates

    def clean_dataset(self, remove_invalid=False):
        """Run full cleaning pipeline on the dataset."""
        self.report = {
            'total_scanned': 0, 'valid': 0, 'corrupted': 0,
            'duplicates': 0, 'removed': 0, 'issues': [],
        }

        if not os.path.exists(self.images_dir):
            return self.report

        # Validate all images
        for fname in sorted(os.listdir(self.images_dir)):
            fpath = os.path.join(self.images_dir, fname)
            if not os.path.isfile(fpath) or not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue

            self.report['total_scanned'] += 1
            result = self.validate_image(fpath)

            if result['valid']:
                self.report['valid'] += 1
            else:
                self.report['corrupted'] += 1
                self.report['issues'].append({'file': fname, 'issues': result['issues']})
                if remove_invalid:
                    os.remove(fpath)
                    self.report['removed'] += 1

        # Find duplicates
        dupes = self.find_duplicates()
        self.report['duplicates'] = len(dupes)
        if dupes:
            self.report['issues'].extend([
                {'file': d['file'], 'issues': [f'Duplicate of {d["duplicate_of"]}']}
                for d in dupes
            ])

        return self.report
