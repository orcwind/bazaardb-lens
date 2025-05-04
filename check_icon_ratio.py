import os
from PIL import Image

def check_icon_ratios():
    icons_dir = 'icons'
    for filename in os.listdir(icons_dir):
        if filename.endswith('.webp'):
            try:
                with Image.open(os.path.join(icons_dir, filename)) as img:
                    width, height = img.size
                    ratio = width / height
                    print(f"{filename}: {width}x{height} (ratio: {ratio:.2f})")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    check_icon_ratios() 