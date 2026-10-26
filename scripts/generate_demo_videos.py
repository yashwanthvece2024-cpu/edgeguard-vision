import cv2
import numpy as np
import os
import math

def draw_gear(img, center, radius, angle, color):
    """Draws a simplified rotating gear."""
    cx, cy = center
    # Draw main body
    cv2.circle(img, center, radius, color, -1)
    cv2.circle(img, center, int(radius * 0.3), (0, 0, 0), -1) # Inner hole
    
    # Draw teeth
    teeth_count = 8
    teeth_length = int(radius * 0.3)
    for i in range(teeth_count):
        theta = angle + i * (2 * math.pi / teeth_count)
        pt1 = (int(cx + radius * math.cos(theta)), int(cy + radius * math.sin(theta)))
        pt2 = (int(cx + (radius + teeth_length) * math.cos(theta - 0.1)), int(cy + (radius + teeth_length) * math.sin(theta - 0.1)))
        pt3 = (int(cx + (radius + teeth_length) * math.cos(theta + 0.1)), int(cy + (radius + teeth_length) * math.sin(theta + 0.1)))
        cv2.fillPoly(img, [np.array([pt1, pt2, pt3])], color)

def generate_video(filename, scenario="normal", frames=150, fps=30):
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    angle1, angle2 = 0.0, 0.5
    speed1, speed2 = 0.1, -0.08
    
    for i in range(frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Apply scenario logic
        if scenario == "anomaly" and 60 <= i <= 90:
            # Simulate a motor stutter/jam by killing speed temporarily
            current_speed1 = 0
            current_speed2 = 0
        else:
            current_speed1 = speed1
            current_speed2 = speed2
            
        angle1 += current_speed1
        angle2 += current_speed2
        
        # Base frame drawing
        temp_frame = np.zeros((height, width, 3), dtype=np.uint8)
        draw_gear(temp_frame, (200, 240), 80, angle1, (150, 150, 150))
        draw_gear(temp_frame, (420, 240), 100, angle2, (100, 150, 200))
        
        if scenario == "shake":
            # Simulate whole-camera mechanical vibration
            dx = int(np.random.normal(0, 5))
            dy = int(np.random.normal(0, 5))
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(temp_frame, M, (width, height))
        else:
            frame = temp_frame
            
        out.write(frame)
        
    out.release()
    print(f"Generated {filename} ({scenario} scenario)")

if __name__ == "__main__":
    # Create the test_data directory at the root of the project
    os.makedirs("test_data", exist_ok=True)
    print("Generating synthetic industrial test videos...")
    generate_video("test_data/01_normal_rotation.mp4", "normal")
    generate_video("test_data/02_stutter_anomaly.mp4", "anomaly")
    generate_video("test_data/03_camera_shake.mp4", "shake")
    print("Dataset generation complete.")