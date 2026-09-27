from ultralytics import YOLO
import cv2

# Load pre-trained YOLO model
model = YOLO("yolov8n.pt")   # 'n' = nano (fastest)

# Load image
img = cv2.imread("image.jpg")

# Run detection
results = model(img)

# Show results
annotated_img = results[0].plot()

cv2.imshow("YOLO Detection", annotated_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
