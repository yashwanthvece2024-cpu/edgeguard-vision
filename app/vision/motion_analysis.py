import cv2
import numpy as np

def compute_optical_flow_stats(frames: list):
    """Calculates dense optical flow and returns stats, confidence, and timeline data."""
    magnitudes = []
    
    for i in range(len(frames) - 1):
        prev = frames[i]
        curr = frames[i+1]
        
        flow = cv2.calcOpticalFlowFarneback(prev, curr, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        avg_mag = np.mean(mag)
        magnitudes.append(avg_mag)
        
    magnitudes = np.array(magnitudes)
    var = round(float(np.var(magnitudes)), 4)
    
    # Calculate a heuristic confidence score (0.0 to 1.0) based on signal variance
    confidence = min(0.99, max(0.40, (var / 5.0) + 0.40)) 
    
    # Downsample timeline data for lightweight frontend Canvas rendering (max ~150 points)
    step = max(1, len(magnitudes) // 150)
    timeline = [round(float(m), 3) for m in magnitudes[::step]]

    return {
        "mean_motion": round(float(np.mean(magnitudes)), 4),
        "max_motion": round(float(np.max(magnitudes)), 4),
        "variance": var,
        "confidence": round(confidence, 2),
        "timeline": timeline
    }

def detect_regions_of_interest(frames: list):
    """Uses frame differencing to find the bounding box of the most active region."""
    mid_idx = len(frames) // 2
    diff = cv2.absdiff(frames[0], frames[mid_idx])
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
        
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    padding = 20
    x, y = max(0, x - padding), max(0, y - padding)
    w, h = w + (padding*2), h + (padding*2)
    return (x, y, w, h)