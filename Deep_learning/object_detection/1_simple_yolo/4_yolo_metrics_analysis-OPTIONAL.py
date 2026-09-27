"""
YOLO METRICS ANALYSIS - PRACTICAL EXAMPLES FOR STUDENTS
This script demonstrates practical ways to use YOLO detection metrics
for data analysis, filtering, and visualization.
"""

from ultralytics import YOLO
import cv2
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

# ==================== LOAD MODEL & IMAGE ====================
model = YOLO("yolov8n.pt")
img = cv2.imread("image.jpg")
results = model(img)
result = results[0]

print("YOLO METRICS ANALYSIS - PRACTICAL EXAMPLES\n")

# ==================== EXAMPLE 1: CONFIDENCE FILTERING ====================
print("=" * 70)
print("EXAMPLE 1: CONFIDENCE-BASED FILTERING")
print("=" * 70)

confidence_threshold = 0.6
boxes = result.boxes

# Filter detections by confidence
high_confidence_mask = boxes.conf > confidence_threshold
filtered_boxes = boxes[high_confidence_mask]

print(f"\nOriginal detections: {len(boxes)}")
print(f"Detections with confidence > {confidence_threshold}: {len(filtered_boxes)}")
print(f"Removed ({len(boxes) - len(filtered_boxes)} low-confidence detections)")

if len(filtered_boxes) > 0:
    print(f"Remaining confidence range: {filtered_boxes.conf.min():.4f} - {filtered_boxes.conf.max():.4f}")

# ==================== EXAMPLE 2: COUNT OBJECTS BY CLASS ====================
print("\n" + "=" * 70)
print("EXAMPLE 2: COUNTING OBJECTS BY CLASS")
print("=" * 70)

class_counts = {}
for cls_id in result.boxes.cls:
    cls_id = int(cls_id)
    class_name = result.names[cls_id]
    class_counts[class_name] = class_counts.get(class_name, 0) + 1

print("\nObject counts by class:")
for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
    percentage = (count / len(result.boxes)) * 100
    print(f"  {class_name:20s}: {count:3d} objects ({percentage:5.1f}%)")

# ==================== EXAMPLE 3: SIZE-BASED FILTERING ====================
print("\n" + "=" * 70)
print("EXAMPLE 3: SIZE-BASED FILTERING (Remove Small Detections)")
print("=" * 70)

# Calculate box areas
box_areas = result.boxes.xywh[:, 2] * result.boxes.xywh[:, 3]
image_area = result.orig_img.shape[0] * result.orig_img.shape[1]
min_area_threshold = image_area * 0.001  # 0.1% of image

large_box_mask = box_areas > min_area_threshold
large_boxes = result.boxes[large_box_mask]

print(f"\nMinimum box area threshold: {min_area_threshold:.0f} pixels")
print(f"Original detections: {len(result.boxes)}")
print(f"Detections after size filtering: {len(large_boxes)}")
print(f"Removed {len(result.boxes) - len(large_boxes)} small/noise detections")

# ==================== EXAMPLE 4: SPATIAL ANALYSIS ====================
print("\n" + "=" * 70)
print("EXAMPLE 4: SPATIAL ANALYSIS - OBJECT DISTRIBUTION")
print("=" * 70)

# Divide image into 9 regions (3x3 grid)
h, w = result.orig_img.shape[:2]
grid_h, grid_w = h // 3, w // 3

region_counts = np.zeros((3, 3), dtype=int)
centers = result.boxes.xywh[:, :2]

for center in centers:
    x, y = int(center[0]), int(center[1])
    region_i = min(y // grid_h, 2)
    region_j = min(x // grid_w, 2)
    region_counts[region_i, region_j] += 1

print("\nObject distribution across 3x3 grid:")
print("(Each cell represents 1/9 of the image)")
print(region_counts)
print("\nVisualization:")
for i in range(3):
    row_str = ""
    for j in range(3):
        row_str += f" [{region_counts[i, j]}] "
    print(row_str)

# ==================== EXAMPLE 5: CONFIDENCE STATISTICS ====================
print("\n" + "=" * 70)
print("EXAMPLE 5: CONFIDENCE ANALYSIS BY CLASS")
print("=" * 70)

print("\nDetailed confidence statistics by class:")
print(f"{'Class':<20} {'Count':>6} {'Mean Conf':>12} {'Min':>8} {'Max':>8} {'Std Dev':>10}")
print("-" * 70)

for cls_id in np.unique(result.boxes.cls.cpu().numpy()):
    cls_id = int(cls_id)
    class_name = result.names[cls_id]
    
    class_mask = result.boxes.cls == cls_id
    class_confs = result.boxes.conf[class_mask]
    
    print(f"{class_name:<20} {class_mask.sum():>6d} {class_confs.mean():>12.4f} "
          f"{class_confs.min():>8.4f} {class_confs.max():>8.4f} {class_confs.std():>10.4f}")


print("\n" + "=" * 70)
print("Analysis complete!")
print("=" * 70 + "\n")
