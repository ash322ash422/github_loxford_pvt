from ultralytics import YOLO
import cv2
import numpy as np

# ==================== LOAD MODEL ====================
model = YOLO("yolov8n.pt")   # 'n' = nano (fastest)

# ==================== LOAD IMAGE ====================
img = cv2.imread("image.jpg")

# ==================== RUN DETECTION ====================
results = model(img)

# ==================== EXTRACT AND PRINT METRICS ====================
print("\n" + "="*70)
print("YOLO MODEL DETECTION METRICS & ANALYSIS")
print("="*70)

# Get the first (and usually only) result
result = results[0]

# --- 1. IMAGE INFORMATION ---
print("\n[1] IMAGE INFORMATION")
print(f"    Image shape: {result.orig_img.shape}")  # (height, width, channels)
print(f"    Image size: Height={result.orig_img.shape[0]}, Width={result.orig_img.shape[1]}")

# --- 2. DETECTION RESULTS OVERVIEW ---
print("\n[2] DETECTION OVERVIEW")
print(f"    Number of detections: {len(result.boxes)}")
print(f"    Classes detected: {result.names}")  # Dictionary of class IDs and names

# --- 3. BOUNDING BOX INFORMATION ---
if len(result.boxes) > 0:
    print("\n[3] DETAILED BOUNDING BOX INFORMATION")
    
    boxes = result.boxes
    
    # Get different box format representations
    print("\n    Box Formats Available:")
    print(f"    - xyxy (x_min, y_min, x_max, y_max): {boxes.xyxy[:3]}...")  # First 3
    print(f"    - xywh (x_center, y_center, width, height): {boxes.xywh[:3]}...")
    # print(f"    - xyn (normalized 0-1): {boxes.xyn[:3]}...")
    
    # --- 4. CONFIDENCE SCORES ---
    print("\n[4] CONFIDENCE SCORES (Object Detection Confidence)")
    for idx, (conf, cls_id) in enumerate(zip(boxes.conf, boxes.cls)):
        class_name = result.names[int(cls_id)]
        print(f"    Detection #{idx+1}: Class='{class_name}' | Confidence={conf:.4f} ({conf*100:.2f}%)")
    
    # Aggregate confidence statistics
    print(f"\n    Confidence Statistics:")
    print(f"    - Mean confidence: {boxes.conf.mean():.4f}")
    print(f"    - Min confidence: {boxes.conf.min():.4f}")
    print(f"    - Max confidence: {boxes.conf.max():.4f}")
    print(f"    - Std deviation: {boxes.conf.std():.4f}")
    
    # --- 5. CLASS INFORMATION ---
    print("\n[5] CLASS & OBJECT INFORMATION")
    unique_classes = np.unique(boxes.cls.cpu().numpy())
    for cls_id in unique_classes:
        class_name = result.names[int(cls_id)]
        count = (boxes.cls == cls_id).sum().item()
        avg_conf = boxes.conf[boxes.cls == cls_id].mean().item()
        print(f"    - {class_name}: {count} object(s), Avg Confidence: {avg_conf:.4f}")
    
    # --- 6. BOUNDING BOX SIZE ANALYSIS ---
    print("\n[6] BOUNDING BOX SIZE ANALYSIS")
    box_areas = boxes.xywh[:, 2] * boxes.xywh[:, 3]  # width * height
    box_areas_normalized = (box_areas / (result.orig_img.shape[0] * result.orig_img.shape[1])) * 100
    
    print(f"    Box Area Statistics (pixels):")
    print(f"    - Mean area: {box_areas.mean():.2f}")
    print(f"    - Min area: {box_areas.min():.2f}")
    print(f"    - Max area: {box_areas.max():.2f}")
    print(f"    - Std deviation: {box_areas.std():.2f}")
    print(f"    - Normalized area (% of image): {box_areas_normalized.mean():.2f}%")
    
    # --- 7. SPATIAL DISTRIBUTION ---
    print("\n[7] SPATIAL DISTRIBUTION")
    centers_xy = boxes.xywh[:, :2]
    print(f"    Object centers (x, y) in pixels:")
    for idx, center in enumerate(centers_xy[:5]):  # Show first 5
        print(f"    - Object {idx+1}: ({center[0]:.1f}, {center[1]:.1f})")
    if len(centers_xy) > 5:
        print(f"    ... and {len(centers_xy)-5} more objects")
    
    # --- 8. INFERENCE SPEED ---
    print("\n[8] INFERENCE PERFORMANCE")
    print(f"    Inference time: {result.speed['inference']:.2f} ms")
    print(f"    Pre-processing time: {result.speed['preprocess']:.2f} ms")
    print(f"    Post-processing time: {result.speed['postprocess']:.2f} ms")
    total_time = sum(result.speed.values())
    print(f"    Total pipeline time: {total_time:.2f} ms")
    fps = 1000 / total_time if total_time > 0 else 0
    print(f"    Estimated FPS: {fps:.2f}")
    
    # --- 9. ADDITIONAL METRICS ---
    print("\n[9] ADDITIONAL AVAILABLE METRICS")
    print(f"    Has masks: {result.masks is not None}")
    print(f"    Has keypoints: {result.keypoints is not None}")
    # print(f"    Model input shape: {result.shape}")
    print(f"Original image shape: {result.orig_img.shape}")

else:
    print("\n[!] No objects detected in this image")

# --- 10. USE CASES FOR ANALYSIS ---
print("\n" + "="*70)
print("USE CASES FOR FURTHER ANALYSIS:")
print("="*70)
print("""
1. FILTERING BY CONFIDENCE:
   - Filter detections with confidence > threshold
   - Improve precision by removing low-confidence predictions
   
2. CLASS-BASED COUNTING:
   - Count specific object types
   - Build histograms of detected classes
   
3. SPATIAL ANALYSIS:
   - Track object density in different image regions
   - Detect clustering patterns
   - Monitor crowd behavior
   
4. SIZE-BASED FILTERING:
   - Remove small noise detections (size filtering)
   - Focus on objects of interest
   - Detect anomalies in object sizes
   
5. PERFORMANCE OPTIMIZATION:
   - Monitor inference speed
   - Optimize batch processing
   - Choose appropriate model sizes
   
6. QUALITY METRICS:
   - Calculate detection accuracy metrics
   - Compare model performance
   - Generate performance reports
   
7. VISUALIZATION:
   - Draw bounding boxes with confidence scores
   - Create heatmaps of object locations
   - Generate annotated images for review
""")
print("="*70 + "\n")

# ==================== VISUALIZE RESULTS ====================
annotated_img = result.plot()

cv2.imshow("YOLO Detection", annotated_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
