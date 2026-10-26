import cv2
import os

def validate_opencv_version():
    """Enforce OpenCV 5 requirement strictly on boot per competition rules."""
    version = cv2.__version__
    if not version.startswith("5."):
        raise RuntimeError(f"FATAL: OpenCV 5 required. Found version: {version}. Check requirements.txt")
    return version

def extract_frames(video_path: str, max_frames: int = 150, scale_factor: float = 1.0, skip_frames: int = 0, roi=None):
    """Safely ingest video, scale, optionally skip frames, and optionally crop to an ROI."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Failed to open video.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret or len(frames) >= max_frames:
            break
            
        if count % (skip_frames + 1) == 0:
            if roi:
                x, y, w, h = roi
                # Ensure bounds
                h_img, w_img = frame.shape[:2]
                y2, x2 = min(y+h, h_img), min(x+w, w_img)
                frame = frame[y:y2, x:x2]
                
            if scale_factor != 1.0:
                h_img, w_img = frame.shape[:2]
                frame = cv2.resize(frame, (int(w_img * scale_factor), int(h_img * scale_factor)))
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append(gray)
            
        count += 1
        
    cap.release()
    if len(frames) < 2:
        raise ValueError("Insufficient usable frames extracted.")
        
    return frames, fps