from PIL import Image, ImageDraw
import os

def create_desktop_icon():
    # 1. Create a 256x256 image with our Zen/Satisfying dark background
    size = 256
    img = Image.new('RGB', (size, size), color=(10, 10, 15))
    draw = ImageDraw.Draw(img)

    # 2. Draw a subtle background grid
    for i in range(0, size, 32):
        draw.line([(i, 0), (i, size)], fill=(40, 40, 50), width=2)
        draw.line([(0, i), (size, i)], fill=(40, 40, 50), width=2)

    # 3. Draw the main Neon Cyan Block in the center
    # Add a pseudo-3D border for that satisfying look
    padding = 48
    draw.rectangle(
        [padding, padding, size - padding, size - padding], 
        fill=(0, 255, 255),  # Neon Cyan
        outline=(255, 255, 255), # White edge
        width=4
    )

    # 4. Ensure the assets folder exists
    if not os.path.exists("assets"):
        os.makedirs("assets")

    # 5. Save it as a multi-resolution Windows Icon file
    icon_sizes = [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]
    save_path = os.path.join("assets", "blockstacker.ico")
    img.save(save_path, format="ICO", sizes=icon_sizes)
    print(f"Success! Desktop icon saved to: {save_path}")

if __name__ == "__main__":
    create_desktop_icon()