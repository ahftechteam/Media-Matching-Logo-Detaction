from ultralytics import YOLO
import numpy as np

# Load the YOLOv8 model
# model = YOLO('model/yolov8s.pt')
model = YOLO('model/AyatLogoTracker.pt')

class VideoUtils:
    # Define allowed video extensions
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

    @staticmethod
    def allowed_file(filename):
        # Check if the file has one of the allowed extensions
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in VideoUtils.ALLOWED_EXTENSIONS

    # Function to process the image with YOLOv8
    def detect_objects(image):
        # Run YOLOv8 model inference
        results = model(image)
        
        # Convert YOLOv8 results into a more readable format
        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls[0])  # Get the class ID of the detected object
                confidence = box.conf[0].item()  # Confidence score
                label = model.names[class_id] if model.names else str(class_id)  # Get class name or use class ID
                detections.append({
                    'label': label,
                    # 'confidence': round(confidence, 0.75),
                    'confidence': 0.75,
                    'box': [x1, y1, x2, y2]
                })
        return detections