"""Create test images for video generation."""
from PIL import Image, ImageDraw
import numpy as np
from pathlib import Path

img_dir = Path("/Users/greglind/Projects/NullRecords/nullrecords-website/ai-engine/media-library/images")
img_dir.mkdir(parents=True, exist_ok=True)

# Image 1: Cyberpunk city gradient with geometric shapes
img1 = Image.new("RGB", (2000, 2000))
draw1 = ImageDraw.Draw(img1)
for y in range(2000):
    r = int(10 + 30 * (y / 2000))
    g = int(0 + 15 * (y / 2000))
    b = int(40 + 80 * (y / 2000))
    draw1.line([(0, y), (2000, y)], fill=(r, g, b))
draw1.rectangle([200, 300, 1800, 1700], outline=(0, 255, 255), width=4)
draw1.rectangle([300, 400, 1700, 1600], outline=(255, 87, 88), width=3)
draw1.line([(100, 1000), (1900, 1000)], fill=(237, 117, 18), width=3)
draw1.line([(1000, 200), (1000, 1800)], fill=(0, 255, 65), width=2)
for x in range(200, 1800, 100):
    draw1.line([(x, 800), (x, 1200)], fill=(0, 255, 255), width=1)
for yy in range(800, 1200, 50):
    draw1.line([(200, yy), (1800, yy)], fill=(0, 255, 255), width=1)
for cx, cy, color in [(500, 600, (255, 0, 100)), (1500, 500, (0, 200, 255)), (1000, 1400, (255, 150, 0))]:
    for rr in range(80, 0, -2):
        draw1.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=color)
img1.save(str(img_dir / "cyber_grid.jpg"), quality=90)
print("Created: cyber_grid.jpg")

# Image 2: Dark abstract with light streaks
img2 = Image.new("RGB", (2000, 2000), (5, 5, 15))
draw2 = ImageDraw.Draw(img2)
rng = np.random.default_rng(42)
for _ in range(30):
    x1, y1 = int(rng.integers(0, 2000)), int(rng.integers(0, 2000))
    angle = float(rng.uniform(0, np.pi * 2))
    length = int(rng.integers(300, 1500))
    x2 = int(x1 + length * np.cos(angle))
    y2 = int(y1 + length * np.sin(angle))
    colors = [(0, 255, 255), (255, 87, 88), (237, 117, 18), (0, 255, 65)]
    color_choice = colors[int(rng.integers(0, 4))]
    draw2.line([(x1, y1), (x2, y2)], fill=color_choice, width=int(rng.integers(1, 4)))
for _ in range(15):
    cx, cy = int(rng.integers(0, 2000)), int(rng.integers(0, 2000))
    rr = int(rng.integers(100, 400))
    draw2.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(10, 10, 30))
img2.save(str(img_dir / "light_streaks.jpg"), quality=90)
print("Created: light_streaks.jpg")

# Image 3: Diamond pattern with halftone dots
img3 = Image.new("RGB", (2000, 2000), (10, 0, 20))
draw3 = ImageDraw.Draw(img3)
for y in range(0, 2000, 2):
    t = y / 2000
    r = int(20 * t)
    g = int(10 * t)
    b = int(60 * t + 20)
    draw3.line([(0, y), (2000, y)], fill=(r, g, b))
draw3.polygon([(1000, 200), (1800, 1000), (1000, 1800), (200, 1000)], outline=(0, 255, 255), width=5)
draw3.polygon([(1000, 400), (1600, 1000), (1000, 1600), (400, 1000)], outline=(255, 87, 88), width=3)
for x in range(100, 1900, 80):
    for y in range(100, 1900, 80):
        dist = ((x - 1000) ** 2 + (y - 1000) ** 2) ** 0.5
        if dist < 700:
            draw3.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 255, 255))
img3.save(str(img_dir / "null_record_art.jpg"), quality=90)
print("Created: null_record_art.jpg")

print("\nAll test images created!")
for f in sorted(img_dir.glob("*")):
    print(f"  {f.name} ({f.stat().st_size / 1024:.1f} KB)")
