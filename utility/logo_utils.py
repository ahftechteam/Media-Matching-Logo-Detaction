import cv2
import json
from flask import jsonify
from ultralytics import YOLO
from datetime import timedelta
import requests

class LogoUtils:
    def format_time(seconds):
        return str(timedelta(seconds=float(seconds))).split('.')[0]

    def send_detection_results(url, data):
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses
            print(f"Successfully sent data to {url}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send data: {e}")

    def process_video(config):
        model = YOLO(config['detection_model_path'])
        video_capture = cv2.VideoCapture(config['video_path'])

        if not video_capture.isOpened():
            print(f"Error opening video file: {config['video_path']}")
            return

        # Get video properties
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

        unique_detections = {}
        frame_id = 0
        confidence_threshold = 0.99
        logo_appearances = []
        current_appearance = None

        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            frame_id += 1
            results = model(frame, conf=confidence_threshold)[0]  # Only process first image in batch

            logo_detected = False
            for detection in results.boxes.data:
                x1, y1, x2, y2, confidence, _ = detection.tolist()
                if confidence > confidence_threshold:
                    logo_detected = True
                    timestamp = frame_id / fps
                    
                    # Create a unique key for this bounding box
                    bbox_key = f"{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}"
                    
                    if bbox_key not in unique_detections:
                        unique_detections[bbox_key] = {
                            "first_frame_id": frame_id,
                            "first_timestamp": f"{timestamp:.2f}",
                            "logo_name": config['logo_name'],
                            "bounding_box": {
                                "x1": int(x1),
                                "y1": int(y1),
                                "x2": int(x2),
                                "y2": int(y2)
                            },
                            "highest_confidence": float(confidence)
                        }
                    else:
                        # Update the highest confidence if this detection has higher confidence
                        if confidence > unique_detections[bbox_key]["highest_confidence"]:
                            unique_detections[bbox_key]["highest_confidence"] = float(confidence)
                    
                    break  # We only need one detection per frame to consider the logo as detected

            if logo_detected:
                if current_appearance is None:
                    current_appearance = {"start_frame": frame_id, "start_time": frame_id / fps}
            elif current_appearance is not None:
                current_appearance["end_frame"] = frame_id - 1
                current_appearance["end_time"] = (frame_id - 1) / fps
                current_appearance["duration"] = current_appearance["end_time"] - current_appearance["start_time"]
                logo_appearances.append(current_appearance)
                current_appearance = None

            # Optional: Print progress
            if frame_id % 100 == 0:
                print(f"Processed {frame_id}/{total_frames} frames")

        # Handle case where video ends while logo is still detected
        if current_appearance is not None:
            current_appearance["end_frame"] = frame_id
            current_appearance["end_time"] = frame_id / fps
            current_appearance["duration"] = current_appearance["end_time"] - current_appearance["start_time"]
            logo_appearances.append(current_appearance)

        video_capture.release()

        # Format logo appearances
        formatted_appearances = []
        for appearance in logo_appearances:
            formatted_appearances.append({
                "videoInputId": config['videoInputId'],
                "start_time": LogoUtils.format_time(appearance["start_time"]),
                "end_time": LogoUtils.format_time(appearance["end_time"]),
                "duration": LogoUtils.format_time(appearance["duration"]),
                "start_frame": appearance["start_frame"],
                "end_frame": appearance["end_frame"],
            })

        # Send the formatted appearances to another server
        LogoUtils.send_detection_results(config['post_url'], formatted_appearances)
    
        return json.dumps(formatted_appearances, indent=4)

