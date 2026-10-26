import os
import uuid
import shutil
import sqlite3
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.vision.video_io import validate_opencv_version
from app.vision.agent import AdaptiveAgent

app = FastAPI(title="EdgeGuard Vision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
DB_PATH = "edgeguard_history.db"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inspections
                 (id TEXT PRIMARY KEY, timestamp TEXT, filename TEXT, status TEXT, 
                  scans INTEGER, variance REAL, confidence REAL, full_result TEXT)''')
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    version = validate_opencv_version()
    init_db()
    print(f"[*] EdgeGuard Vision initialized successfully with OpenCV {version}")

@app.get("/health")
def health_check():
    import cv2
    return {"status": "healthy", "opencv_version": cv2.__version__, "mode": "Local SQLite"}

@app.get("/api/stats")
def get_stats():
    """Serves real data for the advanced Overview tab."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) FROM inspections GROUP BY status")
    all_time = dict(c.fetchall())
    
    conn.row_factory = sqlite3.Row
    c2 = conn.cursor()
    c2.execute("SELECT id, timestamp, filename, status, scans, variance, confidence FROM inspections ORDER BY timestamp DESC LIMIT 5")
    recent = [dict(row) for row in c2.fetchall()]
    latest = recent[0] if recent else None
    conn.close()
    
    total = sum(all_time.values())
    anomalies = all_time.get("COMPLETED_ANOMALY", 0)
    stable = all_time.get("COMPLETED_STABLE", 0) + all_time.get("COMPLETED_FALSE_POSITIVE", 0)
    uncertain = all_time.get("UNCERTAIN", 0)
    
    return {
        "metrics": {"total": total, "anomalies": anomalies, "stable": stable, "uncertain": uncertain},
        "recent": recent,
        "latest": latest
    }

@app.get("/api/history")
def get_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, timestamp, filename, status, scans, variance, confidence FROM inspections ORDER BY timestamp DESC LIMIT 50")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"history": rows}

@app.get("/api/evaluate")
def evaluate_lab():
    """Runs evaluation against synthetic test fixtures with crash protection."""
    fixtures = ["test_data/01_normal_rotation.mp4", "test_data/02_stutter_anomaly.mp4", "test_data/03_camera_shake.mp4"]
    results = []
    agent = AdaptiveAgent(variance_threshold=0.05, global_motion_threshold=5.0)
    
    for fix in fixtures:
        if not os.path.exists(fix):
            results.append({"file": fix.split('/')[-1], "status": "FILE_NOT_FOUND", "scans": 0, "variance": 0.0})
            continue
        try:
            res = agent.run_inspection(fix)
            results.append({"file": fix.split('/')[-1], "status": res["status"], "scans": res["scans_performed"], "variance": res["metrics"]["variance"]})
        except Exception as e:
            results.append({"file": fix.split('/')[-1], "status": f"ERROR", "scans": 0, "variance": 0.0, "error": str(e)})
    return {"evaluation": results}

@app.post("/api/analyze")
async def analyze_video(video: UploadFile = File(...)):
    if not video.filename.endswith(('.mp4', '.avi', '.mov')):
        raise HTTPException(status_code=400, detail="Unsupported video format. Use MP4 or AVI.")
        
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{video.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
            
        agent = AdaptiveAgent(variance_threshold=0.05, global_motion_threshold=5.0)
        result = agent.run_inspection(file_path)
        
        # Strip internal temp paths before saving
        for step in result["trace"]:
            if "file" in step["parameters"] and isinstance(step["parameters"]["file"], str):
                step["parameters"]["file"] = video.filename
                
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO inspections VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (file_id, datetime.now().isoformat(), video.filename, 
                   result["status"], result["scans_performed"], 
                   result["metrics"]["variance"], result["metrics"].get("confidence", 0.0),
                   json.dumps(result)))
        conn.commit()
        conn.close()
        
        os.remove(file_path)
        return JSONResponse(content={"analysis_id": file_id, "result": result})
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)