# main.py
import cv2
from ultralytics import YOLO
import time

def main():
    """
    Two‑feed YOLO demo that works cleanly with webcams.

    By default:
      • Feed 1 → camera index 0  (required)
      • Feed 2 → camera index 1  (optional – skipped if not present)
    """
    print("Loading YOLO model...")

    # Prefer your local lightweight model if it exists, otherwise fall back to the default yolov8n.
    try:
        model = YOLO("yolov8n.pt")
        print("Using local model: yolov8n.pt")
    except Exception:
        model = YOLO("yolov8n.pt")
        print("Local yolov8n.pt not found; using default yolov8n.pt")

    cam_index_1 = 0
    cam_index_2 = 1  # second webcam (optional)

    print(f"Opening webcam feeds:\n  1. camera index {cam_index_1}\n  2. camera index {cam_index_2} (optional)")
    cap1 = cv2.VideoCapture(cam_index_1)
    cap2 = cv2.VideoCapture(cam_index_2)

    if not cap1.isOpened():
        print(f"Error: Could not open primary webcam (index {cam_index_1}).")
        return

    if not cap2.isOpened():
        print(f"Warning: Could not open secondary webcam (index {cam_index_2}). Running with a single feed.")
        cap2 = None

    print("Starting demo. Press 'q' in any window to quit.")

    last_t = time.time()
    fps = 0.0

    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = (False, None)
        if cap2 is not None:
            ret2, frame2 = cap2.read()

        if not ret1 and not ret2:
            print("No frames available from any webcam. Exiting.")
            break

        now = time.time()
        dt = now - last_t
        if dt > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / dt)
        last_t = now

        if ret1:
            results1 = model(frame1, verbose=False, imgsz=640, conf=0.3)
            annotated_frame1 = results1[0].plot()
            annotated_frame1 = cv2.resize(annotated_frame1, (640, 480))
            cv2.putText(
                annotated_frame1,
                f"Feed 1  |  FPS: {fps:.1f}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow("Feed 1: Camera 0", annotated_frame1)

            
        if cap2 is not None and ret2:
            results2 = model(frame2, verbose=False, imgsz=640, conf=0.3)
            annotated_frame2 = results2[0].plot()
            annotated_frame2 = cv2.resize(annotated_frame2, (640, 480))
            cv2.putText(
                annotated_frame2,
                "Feed 2: Camera 1",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow("Feed 2: Camera 1", annotated_frame2)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Demo interrupted by user.")
            break

    cap1.release()
    if cap2 is not None:
        cap2.release()
    cv2.destroyAllWindows()
    print("Demo finished.")


if __name__ == "__main__":
    main()