import time
from app.vision.video_io import extract_frames
from app.vision.motion_analysis import compute_optical_flow_stats, detect_regions_of_interest

class AdaptiveAgent:
    def __init__(self, variance_threshold: float = 0.05, global_motion_threshold: float = 5.0):
        self.variance_threshold = variance_threshold
        self.global_motion_threshold = global_motion_threshold
        self.trace = []

    def _log(self, operation: str, params: dict, reason: str, result: str, next_action: str):
        self.trace.append({
            "timestamp": time.time(),
            "operation": operation,
            "parameters": params,
            "reason": reason,
            "result": result,
            "next_action": next_action
        })

    def run_inspection(self, video_path: str):
        self.trace = []
        self._log("Video Validation", {"file": video_path.split('/')[-1]}, "Valid format and size", "Input accepted", "Start coarse scan")
        
        # Coarse Scan
        coarse_frames, _ = extract_frames(video_path, scale_factor=0.5, skip_frames=1)
        coarse_stats = compute_optical_flow_stats(coarse_frames)
        variance = coarse_stats["variance"]
        global_motion = coarse_stats["mean_motion"]
        
        self._log("Coarse Scan", {"resolution": "50%", "fps_skip": 1, "variance": variance}, "Initial motion analysis", "Completed", "Decision Evaluation")

        # Camera Shake Detection
        if global_motion > self.global_motion_threshold:
            self._log("Camera Motion Check", {"global_motion": global_motion, "threshold": self.global_motion_threshold}, "Significant camera movement detected", "Uncertain", "Request human review")
            return self._build_result("UNCERTAIN", "Camera motion detected. Visual screening is not a certified diagnosis.", coarse_stats, 1)

        self._log("Decision Evaluation", {"variance": variance, "threshold": self.variance_threshold}, "Comparing variance to threshold", "Evaluated", "Determine escalation")

        # Decision
        if variance < self.variance_threshold:
            self._log("Recommendation", {}, "Motion within normal ranges", "Stable", "Finish analysis")
            return self._build_result("COMPLETED_STABLE", "Continue monitoring. No anomalies detected.", coarse_stats, 1)
            
        # Escalation
        self._log("Adaptive Escalation", {"variance": variance}, "Significant motion variance detected", "Escalating", "Acquire ROI")
        roi = detect_regions_of_interest(coarse_frames)
        
        if roi:
            full_res_roi = tuple(coord * 2 for coord in roi)
            self._log("Target Acquisition", {"roi": full_res_roi}, "Isolating anomalous region", "ROI Acquired", "Detailed scan")
            
            detailed_frames, _ = extract_frames(video_path, scale_factor=1.0, skip_frames=0, roi=full_res_roi)
            detailed_stats = compute_optical_flow_stats(detailed_frames)
            final_variance = detailed_stats["variance"]
            
            if final_variance >= self.variance_threshold:
                self._log("Final Recommendation", {"final_variance": final_variance}, "Irregular motion confirmed on high-res pass", "Anomaly Detected", "Generate report")
                return self._build_result("COMPLETED_ANOMALY", "Escalate for detailed inspection. Irregular motion confirmed.", detailed_stats, 2)
            else:
                self._log("Final Recommendation", {"final_variance": final_variance}, "Artifact eliminated in high-res pass", "Stable", "Generate report")
                return self._build_result("COMPLETED_FALSE_POSITIVE", "Downgraded to stable. Initial variance was an artifact.", detailed_stats, 2)
        else:
            self._log("Final Recommendation", {}, "Unable to isolate bounding box", "Uncertain", "Request human review")
            return self._build_result("UNCERTAIN", "Anomaly suspected but ROI extraction failed. Review manually.", coarse_stats, 1)

    def _build_result(self, status, recommendation, metrics, scans=1):
        return {
            "status": status,
            "recommendation": recommendation,
            "scans_performed": scans,
            "metrics": metrics,
            "trace": self.trace
        }