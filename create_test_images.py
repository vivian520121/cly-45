"""创建测试图片"""

from pathlib import Path
from PIL import Image
import piexif
import os

test_dir = Path("test_images")
test_dir.mkdir(exist_ok=True)

# 创建带 EXIF 数据的 JPG 图片
exif_dict = {
    "0th": {
        piexif.ImageIFD.Make: b"Test Camera",
        piexif.ImageIFD.Model: b"Test Model X1",
        piexif.ImageIFD.Software: b"TestSoftware 1.0",
        piexif.ImageIFD.Artist: b"Test Author",
        piexif.ImageIFD.DateTime: b"2024:01:15 10:30:00",
    },
    "Exif": {
        piexif.ExifIFD.DateTimeOriginal: b"2024:01:15 10:30:00",
        piexif.ExifIFD.ExposureTime: (1, 200),
        piexif.ExifIFD.FNumber: (28, 10),
        piexif.ExifIFD.ISOSpeedRatings: 100,
        piexif.ExifIFD.FocalLength: (50, 1),
    },
    "GPS": {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: ((39, 1), (54, 1), (30, 1)),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: ((116, 1), (23, 1), (45, 1)),
    },
    "1st": {},
    "thumbnail": None,
}

exif_bytes = piexif.dump(exif_dict)

# 创建 3 张测试 JPG
for i in range(3):
    img = Image.new("RGB", (800, 600), color=(77, 150, 255))
    img.save(test_dir / f"test_image_{i}.jpg", "JPEG", exif=exif_bytes, quality=95)
    print(f"已创建: test_image_{i}.jpg")

# 创建一张 PNG
img_png = Image.new("RGBA", (1024, 768), color=(255, 100, 100, 255))
img_png.save(test_dir / "test_image.png", "PNG")
print("已创建: test_image.png")

# 创建子目录和图片
subdir = test_dir / "subfolder"
subdir.mkdir(exist_ok=True)
img_sub = Image.new("RGB", (1200, 800), color=(100, 255, 100))
img_sub.save(subdir / "sub_image.jpg", "JPEG", exif=exif_bytes, quality=95)
print("已创建: subfolder/sub_image.jpg")

print("\n测试图片创建完成！")
print(f"目录: {test_dir.absolute()}")
