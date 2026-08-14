"""
Download a pre-trained license plate detection model
"""
import os
import urllib.request
import sys

print("Downloading license plate detection model...")

# Option 1: Try from a known source
model_urls = [
    # High quality license plate model
    "https://github.com/niconielsen32/LicensePlateRecognition/raw/main/license_plate_detector.pt",
    # Alternative: smaller model
    "https://github.com/RobertLucian/license-plate-dataset/releases/download/v0.0/license_plate_yolov5.pt",
]

output_path = "yolov5/license_plate.pt"

for idx, url in enumerate(model_urls):
    try:
        print(f"\nAttempt {idx+1}: Downloading from {url}")
        urllib.request.urlretrieve(url, output_path)
        print(f"✓ Successfully downloaded to {output_path}")
        print(f"File size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Failed: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        continue

print("\n⚠ Could not download pre-trained model from any source.")
print("The system will continue to use YOLOv5s general model.")
print("\nTo manually download a license plate model:")
print("1. Visit: https://universe.roboflow.com/roboflow-universe-projects/license-plate-recognition-rxg4e")
print("2. Or train your own using a license plate dataset")
sys.exit(1)
