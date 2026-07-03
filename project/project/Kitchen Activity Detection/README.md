# ChefSense - Kitchen Activity Detection (Flask + YOLOv8)

ChefSense is a Flask-based web app that detects kitchen activities (Chopping, Cooking, Cleaning, Idle) from images, videos, or webcam frames using YOLOv8. It also saves annotated outputs and per-activity time summaries for videos.

## Requirements
- Python 3.11+
- `yolov8n.pt` weights in the project root (already included)

## Quickstart (Windows PowerShell)
```powershell
cd ChefSense
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# Run the app
python app.py
# or
python main.py
```
Open http://localhost:5000 in your browser.

## Project Structure
```
ChefSense/
  app.py            # Flask app (routes/UI)
  main.py           # Alt entry point
  detection.py      # YOLOv8 inference and activity logic
  templates/        # HTML templates (index, results, settings, webcam)
  static/           # JS/CSS
  uploads/          # Uploaded and annotated media
  detection/        # Saved video summaries (JSON/CSV)
  yolov8n.pt        # YOLOv8 nano weights
  requirements.txt
  README.md
```

## Features
- Image upload: detects activity, returns annotated image preview when detections exist
- Video upload: generates an annotated video and saves an activity summary JSON (and CSV on demand)
- Webcam: live detection via browser, returns detections + bounding boxes
- Settings: adjust `confidence_threshold` and `frame_processing_rate` at `/settings`

## Configuration
- Environment variable: `SESSION_SECRET` (optional)
- App settings are persisted in `settings.json` in the project root

## Endpoints
- `GET /` home UI
- `GET /webcam` webcam UI
- `POST /upload_image` upload and analyze an image
- `POST /upload_video` upload and analyze a video
- `POST /detect_webcam` analyze a single webcam frame (base64 JPEG)
- `GET /settings` view settings; `POST /settings` update/reset
- `GET /download_summary/<filename>?format=json|csv` download video summary
- `GET /uploads/<filename>` serve uploaded/annotated files

## Notes and Troubleshooting
- Video writing: the app uses H.264 (`'AVC1'`) for better MP4 compatibility. If writing fails on your system, change the fourcc in `detection.py` from `AVC1` to `mp4v`:
  ```python
  fourcc = cv2.VideoWriter_fourcc(*'mp4v')
  ```
  You may also need FFmpeg installed and available on PATH.
- Large files: uploads are limited to 100 MB by default.
- Torch will be installed as a dependency of `ultralytics`. CPU inference is used by default.

## License
This project is for educational/demo purposes.
