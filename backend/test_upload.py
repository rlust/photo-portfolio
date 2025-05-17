import os
import requests
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000/api"

# Path to a test image (you may need to adjust this)
TEST_IMAGE = "test_image.jpg"

# Create a test folder if it doesn't exist
if not os.path.exists("test_images"):
    os.makedirs("test_images")
    print("Created test_images directory")

# Create a test image if it doesn't exist
test_image_path = os.path.join("test_images", TEST_IMAGE)
if not os.path.exists(test_image_path):
    # Create a simple colored image using PIL
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (800, 600), color='red')
    d = ImageDraw.Draw(img)
    d.text((100, 100), "Test Image", fill='white')
    img.save(test_image_path)
    print(f"Created test image at {test_image_path}")

def test_upload_photo():
    """Test uploading a photo to the API."""
    url = f"{BASE_URL}/photos/upload"
    
    # Prepare the file and data
    with open(test_image_path, 'rb') as f:
        files = {"file": (TEST_IMAGE, f, "image/jpeg")}
        data = {
            "title": "Test Upload",
            "description": "Test image uploaded via script",
            "is_public": True
        }
        
        print(f"Uploading {test_image_path} to {url}")
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            print("Upload successful!")
            print("Response:", response.json())
            return response.json()
        else:
            print(f"Upload failed with status code {response.status_code}")
            print("Response:", response.text)
            return None

def list_photos():
    """List all photos in the database."""
    url = f"{BASE_URL}/photos/"
    print(f"Fetching photos from {url}")
    response = requests.get(url)
    
    if response.status_code == 200:
        photos = response.json()
        print(f"Found {len(photos)} photos")
        for photo in photos:
            print(f"- {photo['title']} (ID: {photo['id']}, Public: {photo['is_public']})")
        return photos
    else:
        print(f"Failed to fetch photos: {response.status_code}")
        print("Response:", response.text)
        return []

if __name__ == "__main__":
    print("=== Testing Photo Upload ===")
    test_upload_photo()
    
    print("\n=== Listing All Photos ===")
    list_photos()
