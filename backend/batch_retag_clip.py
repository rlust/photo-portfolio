import os
from pathlib import Path
from clip_tagger import tag_image_with_clip
import logging
# Import centralized tag configuration
from config.tag_config import CANDIDATE_TAGS, DEFAULT_TOP_K

# Example: you may want to import your database model here
# from your_db_module import get_all_images, update_image_tags

def get_all_local_images(root_dir="uploads"):
    """Yield (folder, filename, path) for all images in uploads/"""
    uploads = Path(root_dir)
    for folder in uploads.iterdir():
        if folder.is_dir():
            for img_file in folder.iterdir():
                if img_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                    yield folder.name, img_file.name, str(img_file)

def main():
    logging.basicConfig(level=logging.INFO)
    for folder, filename, img_path in get_all_local_images():
        try:
            top_tags = tag_image_with_clip(img_path, CANDIDATE_TAGS, top_k=DEFAULT_TOP_K)
            tag_strings = [tag for tag, prob in top_tags]
            logging.info(f"{folder}/{filename}: {tag_strings}")
            # Here, update your DB with tag_strings for (folder, filename)
            # update_image_tags(folder, filename, tag_strings)
        except Exception as e:
            logging.error(f"Failed to tag {folder}/{filename}: {e}")

if __name__ == "__main__":
    main()
