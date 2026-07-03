import cv2
import numpy as np
import logging
import os
from collections import defaultdict
import time
from ultralytics import YOLO
import imageio

class KitchenActivityDetector:
    def __init__(self, confidence_threshold=0.25, frame_processing_rate=1):
        """Initialize the detector with YOLOv8 model"""
        try:
            # Load a pre-trained YOLOv8 model
            self.model = YOLO("yolov8n.pt")
            logging.info("YOLOv8 model loaded successfully.")
            
            # Map COCO class IDs to names
            self.coco_class_names = self.model.names
            
            # Define kitchen object categories based on COCO classes
            self.kitchen_object_categories = {
                'chopping': ['knife', 'scissors'],
                'cooking': ['oven', 'microwave', 'refrigerator', 'cup', 'bowl', 'fork', 'spoon', 'toaster', 'wine glass', 'bottle', 'dining table'],
                'cleaning': ['sink', 'bottle', 'cup', 'bowl', 'toothbrush', 'hair drier', 'vase'] 
            }
            
            self.confidence_threshold = confidence_threshold
            self.frame_processing_rate = frame_processing_rate
            
            logging.info("Kitchen activity detector initialized with YOLOv8")
        except Exception as e:
            logging.error(f"Failed to initialize detector: {str(e)}")
            raise

    def detect_objects(self, frame):
        """Detect objects in a frame using YOLOv8"""
        detections = []
        try:
            # Perform inference
            results = self.model.predict(source=frame, show=False, conf=self.confidence_threshold, verbose=False)
            
            # Process results
            if results:
                for r in results:
                    for box in r.boxes:
                        class_id = int(box.cls[0])
                        class_name = self.coco_class_names[class_id]
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        detections.append({
                            'class': class_name,
                            'confidence': confidence,
                            'bbox': [x1, y1, x2, y2]
                        })
            return detections
            
        except Exception as e:
            logging.error(f"Error detecting objects with YOLOv8: {str(e)}")
            return []

    def draw_bounding_boxes(self, frame, detections):
        """Draw bounding boxes and labels on the frame"""
        try:
            result_frame = frame.copy()
            
            color_map = {
                'knife': (0, 0, 255),      # Red for chopping
                'scissors': (0, 0, 200),
                'oven': (0, 165, 255),     # Orange for cooking
                'microwave': (0, 150, 255),
                'refrigerator': (0, 140, 255),
                'cup': (0, 130, 255),
                'bowl': (0, 120, 255),
                'fork': (0, 110, 255),
                'spoon': (0, 100, 255),
                'toaster': (0, 90, 255),
                'bottle': (255, 255, 0),   # Cyan for cleaning/cooking
                'sink': (255, 200, 0),
                'toothbrush': (255, 150, 0),
                'hair drier': (255, 100, 0),
                'dining table': (0, 255, 0), # Green for general kitchen area
                'person': (0, 255, 0)      # Green for person
            }
            
            for detection in detections:
                class_name = detection['class']
                confidence = detection['confidence']
                bbox = detection['bbox']
                
                x1, y1, x2, y2 = map(int, bbox)
                
                color = color_map.get(class_name, (255, 255, 255)) # Default to white
                
                cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 2)
                
                label = f"{class_name}: {confidence:.2f}"
                
                (text_width, text_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                
                cv2.rectangle(
                    result_frame,
                    (x1, y1 - text_height - 10),
                    (x1 + text_width, y1),
                    color,
                    -1
                )
                
                cv2.putText(
                    result_frame,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )
            
            return result_frame
            
        except Exception as e:
            logging.error(f"Error drawing bounding boxes: {str(e)}")
            return frame

    def classify_activity(self, detections):
        """Classify kitchen activity based on detected objects from YOLOv8"""
        detected_classes = [det['class'].lower() for det in detections]
        
        activity_scores = defaultdict(float)
        
        # First, check for chopping (highest priority)
        for obj_class in self.kitchen_object_categories['chopping']:
            for det in detections:
                if det['class'].lower() == obj_class:
                    activity_scores['Chopping'] += det['confidence']
        
        if activity_scores['Chopping'] > 0:
            return 'Chopping', activity_scores['Chopping'], detected_classes

        # Next, check for cleaning
        for obj_class in self.kitchen_object_categories['cleaning']:
            for det in detections:
                if det['class'].lower() == obj_class:
                    activity_scores['Cleaning'] += det['confidence']
        
        if activity_scores['Cleaning'] > 0:
            return 'Cleaning', activity_scores['Cleaning'], detected_classes

        # Then, check for cooking
        for obj_class in self.kitchen_object_categories['cooking']:
            for det in detections:
                if det['class'].lower() == obj_class:
                    activity_scores['Cooking'] += det['confidence']
        
        if activity_scores['Cooking'] > 0:
            return 'Cooking', activity_scores['Cooking'], detected_classes
            
        # Default to Idle if a person is detected but no specific kitchen activity objects, or if nothing is detected
        if 'person' in detected_classes:
            person_confidence = next((det['confidence'] for det in detections if det['class'].lower() == 'person'), 0.0)
            return 'Idle', person_confidence, detected_classes

        return 'Idle', 0.0, detected_classes

    def detect_activity_from_frame(self, frame):
        """Detect activity from a single frame"""
        detections = self.detect_objects(frame)
        activity, confidence, detected_objects = self.classify_activity(detections)
        return activity, confidence, detected_objects

    def detect_activity_from_image(self, image_path, save_annotated=True):
        """Detect activity from an image file"""
        try:
            frame = cv2.imread(image_path)
            if frame is None:
                raise ValueError("Could not load image")
            
            # Get detections
            detections = self.detect_objects(frame)
            activity, confidence, detected_objects = self.classify_activity(detections)
            
            # Save annotated image with bounding boxes
            if save_annotated and detections:
                annotated_frame = self.draw_bounding_boxes(frame, detections)
                
                # Create annotated filename
                base_name = os.path.splitext(image_path)[0]
                annotated_path = f"{base_name}_annotated.jpg"
                cv2.imwrite(annotated_path, annotated_frame)
                logging.info(f"Saved annotated image: {annotated_path}")
            
            return activity, confidence, detected_objects
            
        except Exception as e:
            logging.error(f"Error processing image {image_path}: {str(e)}")
            raise

    def detect_activity_from_video(self, video_path, progress_callback=None):
        """Process video and return activity summary"""
        cap = None  # Initialize cap to None
        out = None  # OpenCV writer (unused in forced FFmpeg path)
        ffmpeg_writer = None  # imageio writer (primary)
        output_filename = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("Could not open video file")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            try:
                # Handle NaN or invalid values
                if fps is None or fps <= 0 or (isinstance(fps, float) and np.isnan(fps)):
                    fps = 30.0  # Reasonable default
            except Exception:
                fps = 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) > 0 else None
            
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            # Ensure even dimensions for yuv420p encoders
            target_width = frame_width - (frame_width % 2)
            target_height = frame_height - (frame_height % 2)
            if target_width != frame_width or target_height != frame_height:
                logging.info(f"Cropping frames to even size for encoding: {frame_width}x{frame_height} -> {target_width}x{target_height}")

            # Prefer writing MP4 via FFmpeg (imageio) for consistent browser playback
            base_stem = os.path.splitext(os.path.basename(video_path))[0]
            output_filename = f"annotated_{base_stem}.mp4"
            output_path = os.path.join(os.path.dirname(video_path), output_filename)
            try:
                ffmpeg_writer = imageio.get_writer(
                    output_path,
                    format='ffmpeg',
                    mode='I',
                    fps=float(fps),
                    codec='libx264',
                    quality=None,
                    pixelformat='yuv420p',
                    output_params=['-movflags', 'faststart']
                )
                logging.info("Using imageio FFmpeg writer with libx264")
            except Exception as fferr:
                logging.warning(f"FFmpeg writer unavailable: {fferr}. Proceeding without annotated video.")

            activity_durations = defaultdict(float)
            frame_count = 0
            last_activity = 'Idle'
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Process every Nth frame based on frame_processing_rate
                if frame_count % self.frame_processing_rate == 0:
                    detections = self.detect_objects(frame)
                    activity, confidence, _ = self.classify_activity(detections)
                    last_activity = activity
                else:
                    # If not processing, assume previous activity or idle
                    activity = last_activity
                    detections = []  # No new detections

                # Draw bounding boxes and write to output video
                annotated_frame = self.draw_bounding_boxes(frame, detections)
                # Crop to even dims if needed
                if annotated_frame.shape[1] != target_width or annotated_frame.shape[0] != target_height:
                    annotated_frame = annotated_frame[0:target_height, 0:target_width]
                if out is not None:
                    out.write(annotated_frame)
                elif ffmpeg_writer is not None:
                    # Convert BGR (OpenCV) to RGB for imageio and ensure uint8
                    rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                    ffmpeg_writer.append_data(rgb)

                # Update activity duration based on actual time elapsed for this frame
                duration_per_frame = 1.0 / fps # Duration of a single frame
                activity_durations[activity] += duration_per_frame
                
                if frame_count % 30 == 0: # Log every 30 frames for less frequent logging
                    logging.info(f"Processed {frame_count} frames")
                # Report progress more frequently
                if progress_callback and (frame_count % 10 == 0):
                    try:
                        progress_callback(frame_count, total_frames)
                    except Exception:
                        pass
            
            # Convert to regular dict for JSON serialization
            summary = dict(activity_durations)
            
            # Ensure we have some data
            if not summary:
                summary = {'Idle': 0.0}
            
            logging.info(f"Video processing complete. Processed {frame_count} frames")
            if progress_callback:
                try:
                    progress_callback(frame_count, total_frames)
                except Exception:
                    pass
            if (out is not None or ffmpeg_writer is not None) and output_path is not None:
                # Verify file exists and is non-empty
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return summary, os.path.basename(output_path)
                else:
                    logging.warning(f"Annotated video file missing or empty: {output_path}")
            return summary, None
            
        except Exception as e:
            logging.error(f"Error processing video {video_path}: {str(e)}")
            # Always return a safe tuple so callers do not crash on unpack
            return {'Idle': 0.0}, None
        finally: # Ensure cap and out are released even if error occurs
            if cap is not None:
                cap.release()
            if out is not None:
                out.release()
            if ffmpeg_writer is not None:
                try:
                    ffmpeg_writer.close()
                except Exception:
                    pass
