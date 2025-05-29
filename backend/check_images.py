import os
import requests
from pathlib import Path

# Configuration
BACKEND_URL = "https://simplified-backend-839093975626.us-central1.run.app"

def check_uploads_directory():
    """Check if uploads directory exists and list its contents"""
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        print(f"ERROR: Uploads directory '{uploads_dir}' does not exist!")
        return []
    
    files = list(uploads_dir.glob("*"))
    print(f"Found {len(files)} files in uploads directory:")
    
    for i, file_path in enumerate(files[:10]):  # Show first 10 files only
        file_size = file_path.stat().st_size
        print(f"  {i+1}. {file_path.name} ({file_size / 1024:.1f} KB)")
    
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more files")
    
    return files

def check_image_access(files):
    """Try to access images via HTTP to verify they're publicly accessible"""
    print("\nChecking if files are accessible via HTTP:")
    
    for i, file_path in enumerate(files[:5]):  # Check first 5 files only
        filename = file_path.name
        url = f"{BACKEND_URL}/uploads/{filename}"
        
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {filename} is accessible (Status: {response.status_code})")
                print(f"     URL: {url}")
            else:
                print(f"  ❌ {filename} returned status code {response.status_code}")
                print(f"     URL: {url}")
        except requests.RequestException as e:
            print(f"  ❌ {filename} error: {str(e)}")

def main():
    print("=== Image Accessibility Check ===")
    files = check_uploads_directory()
    
    if files:
        check_image_access(files)
    else:
        print("No files to check. Please upload some images first.")
    
    print("\nRecommendations:")
    print("1. If images are not accessible, check that the 'uploads' directory exists")
    print("2. Ensure the backend is properly serving static files from the 'uploads' directory")
    print("3. Verify CORS settings allow access to /uploads/* paths")
    print("4. Check that the image URLs in the frontend match the actual file paths on the backend")

if __name__ == "__main__":
    main()
