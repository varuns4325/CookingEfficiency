import os
import json
import csv
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from detection import KitchenActivityDetector
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Settings file path
SETTINGS_FILE = 'settings.json'

# Default settings
DEFAULT_SETTINGS = {
    'confidence_threshold': 0.25,
    'frame_processing_rate': 1
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            try:
                settings = json.load(f)
                # Validate loaded settings and apply defaults if keys are missing
                for key, default_value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = default_value
                return settings
            except json.JSONDecodeError:
                logging.error("Error decoding settings.json. Using default settings.")
                return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# Load settings at startup
current_settings = load_settings()
logging.info(f"Loaded settings: {current_settings}")

# Configuration
UPLOAD_FOLDER = 'uploads'
DETECTION_FOLDER = 'detection'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DETECTION_FOLDER'] = DETECTION_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload and detection directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DETECTION_FOLDER, exist_ok=True)

# Initialize detector
detector = KitchenActivityDetector(
    confidence_threshold=current_settings['confidence_threshold'],
    frame_processing_rate=current_settings['frame_processing_rate']
)

# In-memory progress store: {job_id: {processed, total}}
progress_store = {}

def update_progress(job_id):
    def _cb(processed, total):
        progress_store[job_id] = {
            'processed': int(processed),
            'total': int(total) if total is not None else None,
            'timestamp': datetime.now().isoformat()
        }
    return _cb

def allowed_file(filename, file_type='image'):
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    if file_type == 'image':
        return extension in ALLOWED_IMAGE_EXTENSIONS
    elif file_type == 'video':
        return extension in ALLOWED_VIDEO_EXTENSIONS
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webcam')
def webcam():
    return render_template('webcam.html')

@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename, 'image'):
            flash('Invalid file type. Please upload a JPG or PNG image.', 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file
        if not file.filename:
            flash('Invalid filename', 'error')
            return redirect(url_for('index'))
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process image
        activity, confidence, detected_objects = detector.detect_activity_from_image(filepath)
        
        # Check if annotated image exists
        base_name = os.path.splitext(filename)[0]
        annotated_filename = f"{base_name}_annotated.jpg"
        annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_filename)
        
        # Save results
        results = {
            'filename': filename,
            'activity': activity,
            'confidence': float(confidence),
            'detected_objects': detected_objects,
            'timestamp': datetime.now().isoformat(),
            'type': 'image'
        }
        
        # Use annotated image if it exists, otherwise use original
        display_image = annotated_filename if os.path.exists(annotated_path) else filename
        
        return render_template('results.html', results=results, image_path=display_image)
        
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        flash(f'Error processing image: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/upload_video', methods=['POST'])
def upload_video():
    try:
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename, 'video'):
            flash('Invalid file type. Please upload an MP4, AVI, or MOV video.', 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file
        if not file.filename:
            flash('Invalid filename', 'error')
            return redirect(url_for('index'))
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Create a job id (use client-provided if available) and start processing (synchronously here)
        client_job_id = request.form.get('job_id')
        job_id = client_job_id if client_job_id else str(uuid.uuid4())
        progress_store[job_id] = {'processed': 0, 'total': None, 'timestamp': datetime.now().isoformat()}

        # Process video with progress callback (sync). For true async, move to background worker.
        result = detector.detect_activity_from_video(filepath, progress_callback=update_progress(job_id))
        activity_summary, annotated_video_filename = result if isinstance(result, tuple) else (result, None)

        # If annotated video couldn't be created, fall back to original
        is_annotated = True
        if not annotated_video_filename:
            annotated_video_filename = filename
            is_annotated = False
        else:
            # If detector returned a name but file is missing, also fallback
            annotated_full_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_video_filename)
            if not os.path.exists(annotated_full_path):
                logging.warning(f"Annotated video not found at {annotated_full_path}. Falling back to original video.")
                annotated_video_filename = filename
                is_annotated = False
        
        # Save results
        results = {
            'filename': filename,
            'activity_summary': activity_summary,
            'timestamp': datetime.now().isoformat(),
            'type': 'video'
        }
        
        # Save summary to JSON
        summary_filename = f"{timestamp}_video_summary.json"
        summary_path = os.path.join(app.config['DETECTION_FOLDER'], summary_filename)
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        return render_template('results.html', results=results, summary_file=summary_filename, video_path=annotated_video_filename, is_annotated=is_annotated)
        
    except Exception as e:
        logging.error(f"Error processing video: {str(e)}")
        flash(f'Error processing video: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/progress/<job_id>')
def progress(job_id):
    data = progress_store.get(job_id)
    if not data:
        return jsonify({'processed': 0, 'total': None, 'done': False})
    processed = data.get('processed', 0)
    total = data.get('total')
    done = False
    # Heuristic: if timestamp older than 2s and totals known and processed >= total, consider done
    try:
        done = total is not None and processed >= total
    except Exception:
        done = False
    return jsonify({'processed': processed, 'total': total, 'done': done})

@app.route('/detect_webcam', methods=['POST'])
def detect_webcam():
    try:
        # Get frame data from request
        data = request.get_json()
        if not data or 'frame' not in data:
            return jsonify({'error': 'No frame data provided'}), 400
        
        # Decode base64 image
        import base64
        frame_data = data['frame'].split(',')[1]  # Remove data:image/jpeg;base64, prefix
        frame_bytes = base64.b64decode(frame_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Invalid frame data'}), 400
        
        # Detect activity and get full detections with bounding boxes
        detections = detector.detect_objects(frame)
        activity, confidence, detected_objects = detector.classify_activity(detections)
        
        # Format detections for frontend (include bounding boxes)
        formatted_detections = []
        for detection in detections:
            formatted_detections.append({
                'class': detection['class'],
                'confidence': float(detection['confidence']),
                'bbox': detection['bbox']
            })
        
        return jsonify({
            'activity': activity,
            'confidence': float(confidence),
            'detected_objects': detected_objects,
            'detections': formatted_detections,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error processing webcam frame: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global detector
    global current_settings

    if request.method == 'POST':
        if request.is_json and request.json.get('reset'):
            current_settings = DEFAULT_SETTINGS
            save_settings(current_settings)
            flash('Settings reset to default!', 'success')
            # Reinitialize detector with new settings
            detector = KitchenActivityDetector(
                confidence_threshold=current_settings['confidence_threshold'],
                frame_processing_rate=current_settings['frame_processing_rate']
            )
            return jsonify({'success': True})
        
        try:
            confidence_threshold = float(request.form['confidence_threshold'])
            frame_processing_rate = int(request.form['frame_processing_rate'])

            # Basic validation
            if not (0.0 <= confidence_threshold <= 1.0):
                flash('Confidence threshold must be between 0.0 and 1.0.', 'error')
                return redirect(url_for('settings'))
            if not (frame_processing_rate >= 1):
                flash('Frame processing rate must be at least 1.', 'error')
                return redirect(url_for('settings'))

            current_settings['confidence_threshold'] = confidence_threshold
            current_settings['frame_processing_rate'] = frame_processing_rate
            save_settings(current_settings)
            
            # Reinitialize detector with new settings
            detector = KitchenActivityDetector(
                confidence_threshold=current_settings['confidence_threshold'],
                frame_processing_rate=current_settings['frame_processing_rate']
            )
            flash('Settings saved successfully!', 'success')
            return redirect(url_for('settings'))
        except ValueError as e:
            flash(f'Invalid input: {str(e)}. Please enter valid numbers.', 'error')
            return redirect(url_for('settings'))
        except Exception as e:
            logging.error(f"Error saving settings: {str(e)}")
            flash(f'Error saving settings: {str(e)}', 'error')
            return redirect(url_for('settings'))
    
    return render_template('settings.html', settings=current_settings)

@app.route('/download_summary/<filename>')
def download_summary(filename):
    try:
        file_path = os.path.join(app.config['DETECTION_FOLDER'], filename)
        if not os.path.exists(file_path):
            flash('Summary file not found', 'error')
            return redirect(url_for('index'))
        
        # Convert JSON to CSV if requested
        if request.args.get('format') == 'csv':
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            csv_filename = filename.replace('.json', '.csv')
            csv_path = os.path.join(app.config['DETECTION_FOLDER'], csv_filename)
            
            with open(csv_path, 'w', newline='') as csvfile:
                if data['type'] == 'video' and 'activity_summary' in data:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Activity', 'Duration (seconds)', 'Percentage'])
                    for activity, duration in data['activity_summary'].items():
                        total_duration = sum(data['activity_summary'].values())
                        percentage = (duration / total_duration * 100) if total_duration > 0 else 0
                        writer.writerow([activity, duration, f"{percentage:.1f}%"])
            
            return send_file(csv_path, as_attachment=True)
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logging.error(f"Error downloading summary: {str(e)}")
        flash(f'Error downloading summary: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files with correct mime and range support for video."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    mimetype = None
    if ext == 'mp4':
        mimetype = 'video/mp4'
    elif ext == 'webm':
        mimetype = 'video/webm'
    elif ext == 'avi':
        mimetype = 'video/x-msvideo'
    elif ext in {'jpg', 'jpeg'}:
        mimetype = 'image/jpeg'
    elif ext == 'png':
        mimetype = 'image/png'
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        mimetype=mimetype,
        conditional=True
    )

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 100MB.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
