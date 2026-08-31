"""
Module Data — CLUBS Dataset Loader
Downloads and organizes the CLUBS dataset from GitHub.
"""
import os
import json
import requests
from PIL import Image


class DatasetLoader:
    """Handles downloading and organizing the CLUBS dataset."""

    GITHUB_API_URL = 'https://api.github.com/repos/clubs/clubs.github.io/contents/img/objects'
    RAW_BASE_URL = 'https://raw.githubusercontent.com/clubs/clubs.github.io/master/img/objects'

    def __init__(self, dataset_dir):
        self.dataset_dir = dataset_dir
        self.images_dir = os.path.join(dataset_dir, 'images')
        self.metadata_path = os.path.join(dataset_dir, 'metadata.json')
        os.makedirs(self.images_dir, exist_ok=True)

    # Static list of all 85 objects in CLUBS benchmark dataset
    CLUBS_OBJECT_FILES = [
        "000_veet.png", "001_color_pencils.png", "002_cupholder.png", "003_sports_underwear.png",
        "004_axe.png", "005_gleitgel.png", "006_wellness_book.png", "007_smartbox.png",
        "008_denim.png", "009_loreal_gloss.png", "010_veet_creme.png", "011_speedo.png",
        "012_dove_butter.png", "013_sensodyne.png", "014_picture.png", "015_shoebox.png",
        "016_bibi_bottle.png", "017_box.png", "018_wrapping_tape.png", "019_decoration_tape.png",
        "020_yellow_tape.png", "021_envelopes.png", "022_robin_mckelle.png", "023_stanley.png",
        "024_blue.png", "025_best_wishes.png", "026_sauger.png", "027_movie.png",
        "028_gillette.png", "029_trisa.png", "030_toothbrushes.png", "031_crazy_lady.png",
        "032_st_tropez.png", "033_rexona.png", "034_guhl.png", "035_satin_care_gel.png",
        "036_rexona_tropical.png", "037_rexona_invisible.png", "038_syoss.png", "039_huile.png",
        "040_borotalco.png", "041_rexona_diamond.png", "042_borotalco_original.png", "043_brylcreem.png",
        "044_dove_silky.png", "045_clear_scalp.png", "046_borotalco_invisible.png", "047_pantene_pro_shampoo.png",
        "048_signal.png", "049_eos_balls.png", "050_axe_peace.png", "051_garnier_water.png",
        "052_loreal_studio_pro.png", "053_dove_lotion.png", "054_dove_fresh.png", "055_labello.png",
        "056_trisa_flexible.png", "057_elmex.png", "058_trisa_body.png", "059_syoss_shine.png",
        "060_trisa_for_men.png", "061_trisa_classic.png", "062_trisa_fine.png", "063_trisa_fresh.png",
        "064_trisa_pearl.png", "065_trisa_pro.png", "066_trisa_soft.png", "067_trisa_ultra.png",
        "068_trisa_white.png", "069_trisa_wisdom.png", "070_trisa_young.png", "071_trisa_zen.png",
        "072_pantene_repair.png", "073_pantene_volume.png", "074_pantene_smooth.png", "075_pantene_color.png",
        "076_pantene_aqua.png", "077_pantene_classic.png", "078_pantene_curl.png", "079_pantene_daily.png",
        "080_pantene_def.png", "081_pantene_hair.png", "082_pantene_intensive.png", "083_pantene_light.png",
        "084_pantene_shine.png"
    ]

    def get_remote_file_list(self):
        """Fetch the list of object images from the GitHub API or fallback to static catalog."""
        try:
            resp = requests.get(self.GITHUB_API_URL, timeout=10)
            resp.raise_for_status()
            files = resp.json()
            return [
                {
                    'name': f['name'],
                    'download_url': f.get('download_url') or f'{self.RAW_BASE_URL}/{f["name"]}',
                    'size': f.get('size', 0),
                }
                for f in files
                if f['name'].endswith('.png') and f['type'] == 'file'
            ]
        except Exception as e:
            print(f"[DatasetLoader] Using fallback catalog due to API limit ({e})")
            return [
                {
                    'name': fname,
                    'download_url': f'{self.RAW_BASE_URL}/{fname}',
                    'size': 100000,
                }
                for fname in self.CLUBS_OBJECT_FILES
            ]

    def download_image(self, file_info):
        """Download a single image file."""
        filepath = os.path.join(self.images_dir, file_info['name'])
        if os.path.exists(filepath):
            return {'name': file_info['name'], 'status': 'exists', 'path': filepath}

        try:
            resp = requests.get(file_info['download_url'], timeout=60)
            resp.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            return {'name': file_info['name'], 'status': 'downloaded', 'path': filepath}
        except Exception as e:
            return {'name': file_info['name'], 'status': 'error', 'error': str(e)}

    def download_all(self, progress_callback=None):
        """Download or import all CLUBS object images."""
        import shutil

        # First check local objects folder in clubs_dataset_tools-master/objects
        local_objects_dirs = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'clubs_dataset_tools-master', 'objects'),
            os.path.join(self.dataset_dir, '..', 'clubs_dataset_tools-master', 'objects'),
        ]

        copied_count = 0
        for local_dir in local_objects_dirs:
            if os.path.exists(local_dir):
                for fname in os.listdir(local_dir):
                    if fname.endswith('.png'):
                        src = os.path.join(local_dir, fname)
                        dst = os.path.join(self.images_dir, fname)
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)
                            copied_count += 1

        file_list = self.get_remote_file_list()
        results = []
        total = len(file_list)

        for i, file_info in enumerate(file_list):
            result = self.download_image(file_info)
            results.append(result)
            if progress_callback:
                progress_callback(i + 1, total, result)

        # Save metadata
        metadata = {
            'total_files': total,
            'downloaded': sum(1 for r in results if r['status'] in ('downloaded', 'exists')),
            'errors': sum(1 for r in results if r['status'] == 'error'),
            'local_imported': copied_count,
            'files': results,
        }
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def get_local_images(self):
        """List all locally available dataset images."""
        if not os.path.exists(self.images_dir):
            return []

        images = []
        for fname in sorted(os.listdir(self.images_dir)):
            if fname.endswith('.png'):
                fpath = os.path.join(self.images_dir, fname)
                obj_id = fname.split('_')[0]
                obj_name = fname.replace('.png', '').split('_', 1)[-1].replace('_', ' ').title()
                try:
                    img = Image.open(fpath)
                    w, h = img.size
                    images.append({
                        'id': obj_id,
                        'name': obj_name,
                        'filename': fname,
                        'path': fpath,
                        'width': w,
                        'height': h,
                        'size_bytes': os.path.getsize(fpath),
                    })
                except Exception:
                    pass
        return images

    def get_dataset_stats(self):
        """Get statistics about the local dataset."""
        images = self.get_local_images()
        if not images:
            return {'total_images': 0, 'status': 'empty'}

        total_size = sum(img['size_bytes'] for img in images)
        return {
            'total_images': len(images),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'status': 'ready',
            'sample_objects': [img['name'] for img in images[:10]],
        }
