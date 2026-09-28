/**
 * Webcam Analysis Module for Public Speaking Coach
 * Uses MediaPipe FaceMesh via CDN for local-first visual metrics.
 * No video frames are sent to the backend.
 */

class WebcamAnalyzer {
  constructor(videoElement, indicatorElement) {
    this.videoElement = videoElement;
    this.indicatorElement = indicatorElement;
    this.faceMesh = null;
    this.camera = null;
    
    // Metrics
    this.totalFrames = 0;
    this.framesWithFace = 0;
    this.framesWithEyeContact = 0;
    this.postureVariances = [];
    this.expressionVariances = [];
    this.prevLandmarks = null;
    
    this.isRecording = false;
    this.hasPermission = false;
    
    this.faceCountViolations = [];
    this.gazeAwayEvents = [];
    this.multiFaceStart = null;
    this.gazeAwayStart = null;
    this.lastMultiFaceAlert = 0;
    this.lastGazeAlert = 0;
  }

  async initialize() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      this.videoElement.srcObject = stream;
      this.hasPermission = true;

      // Initialize FaceMesh
      this.faceMesh = new FaceMesh({locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
      }});

      this.faceMesh.setOptions({
        maxNumFaces: 3,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      this.faceMesh.onResults(this.onResults.bind(this));

      // Use requestAnimationFrame instead of MediaPipe Camera utility
      // to avoid stream conflicts
      let lastVideoTime = -1;
      const processFrame = async () => {
        if (!this.hasPermission) return;
        if (this.videoElement.readyState >= 2 && this.videoElement.currentTime !== lastVideoTime) {
          lastVideoTime = this.videoElement.currentTime;
          if (this.isRecording) {
            await this.faceMesh.send({image: this.videoElement});
          }
        }
        this.animationFrameId = requestAnimationFrame(processFrame);
      };
      
      processFrame();
      
    } catch (err) {
      console.warn("Webcam permission denied or unavailable:", err);
      this.hasPermission = false;
      if (this.indicatorElement) {
        this.indicatorElement.innerHTML = '<span class="badge bg-secondary">Camera off (Audio only)</span>';
      }
    }
  }

  startRecording() {
    if (!this.hasPermission) return;
    this.isRecording = true;
    this.totalFrames = 0;
    this.framesWithFace = 0;
    this.framesWithEyeContact = 0;
    this.postureVariances = [];
    this.expressionVariances = [];
    this.prevLandmarks = null;
    
    this.faceCountViolations = [];
    this.gazeAwayEvents = [];
    this.multiFaceStart = null;
    this.gazeAwayStart = null;
    this.lastMultiFaceAlert = 0;
    this.lastGazeAlert = 0;
    
    if (this.indicatorElement) {
      this.indicatorElement.innerHTML = '<span class="badge bg-success"><i class="bi bi-camera-video"></i> Tracking Face</span>';
    }
  }

  stopRecording() {
    this.isRecording = false;
    if (this.indicatorElement) {
      this.indicatorElement.innerHTML = '<span class="badge bg-secondary"><i class="bi bi-camera-video-off"></i> Stopped</span>';
    }
    
    // Do NOT stop camera stream so the user can still see themselves
    // if they decide to Retry. The page reload will free resources anyway.
    /*
    if (this.videoElement && this.videoElement.srcObject) {
      this.videoElement.srcObject.getTracks().forEach(t => t.stop());
    }
    */
    
    
    // Close out any active events
    const now = Date.now();
    if (this.multiFaceStart && (now - this.multiFaceStart > 1500)) {
      this.faceCountViolations.push({timestamp: new Date().toISOString(), duration_ms: now - this.multiFaceStart});
    }
    if (this.gazeAwayStart && (now - this.gazeAwayStart > 3500)) {
      this.gazeAwayEvents.push({timestamp: new Date().toISOString(), duration_ms: now - this.gazeAwayStart});
    }

    return this.getMetrics();
  }

  _showToast(message, type) {
    let container = document.getElementById("proctorToastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "proctorToastContainer";
      container.style.position = "fixed";
      container.style.top = "20px";
      container.style.left = "50%";
      container.style.transform = "translateX(-50%)";
      container.style.zIndex = "9999";
      container.style.display = "flex";
      container.style.flexDirection = "column";
      container.style.gap = "10px";
      document.body.appendChild(container);
    }
    
    const toast = document.createElement("div");
    toast.className = `shadow-lg rounded-pill px-4 py-2 mb-0 border-0 text-center`;
    toast.style.background = type === 'danger' ? 'rgba(220, 53, 69, 0.95)' : 'rgba(255, 176, 32, 0.95)';
    toast.style.color = type === 'danger' ? '#fff' : '#1C1B18';
    toast.style.backdropFilter = "blur(10px)";
    toast.style.fontWeight = "600";
    toast.style.transition = "opacity 0.5s ease-in-out";
    toast.style.boxShadow = "0 8px 32px rgba(0,0,0,0.2)";
    toast.innerHTML = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 500);
    }, 4000);
  }

  onResults(results) {
    if (!this.isRecording) return;
    this.totalFrames++;
    const now = Date.now();
    
    // Debug face count
    const faceCount = results.multiFaceLandmarks ? results.multiFaceLandmarks.length : 0;
    if (this.totalFrames % 10 === 0) {
      console.log(`[Debug] Detected faces: ${faceCount}`);
    }

    // Multi-face Detection
    let isMultiFace = false;
    if (faceCount > 1) {
      if (!this.multiFaceStart) {
        this.multiFaceStart = now;
      } else if (now - this.multiFaceStart > 1500) {
        isMultiFace = true;
        if (now - this.lastMultiFaceAlert > 8000) {
          this._showToast("⚠️ Another person detected in frame — please ensure you are alone.", "danger");
          this.lastMultiFaceAlert = now;
        }
      }
    } else {
      if (this.multiFaceStart && (now - this.multiFaceStart > 1500)) {
        this.faceCountViolations.push({
          timestamp: new Date().toISOString(),
          duration_ms: now - this.multiFaceStart
        });
      }
      this.multiFaceStart = null;
    }

    if (faceCount > 0) {
      this.framesWithFace++;
      const landmarks = results.multiFaceLandmarks[0];
      
      const nose = landmarks[1];
      const leftEdge = landmarks[234];
      const rightEdge = landmarks[454];
      
      const leftDist = Math.abs(nose.x - leftEdge.x);
      const rightDist = Math.abs(nose.x - rightEdge.x);
      const ratio = leftDist / rightDist;
      
      let isLookingAway = false;
      if (ratio > 0.6 && ratio < 1.4 && nose.y > 0.2 && nose.y < 0.8) {
        this.framesWithEyeContact++;
      } else {
        isLookingAway = true;
      }
      
      // Gaze Tracking
      let isGazeViolating = false;
      if (isLookingAway) {
        if (!this.gazeAwayStart) {
          this.gazeAwayStart = now;
        } else if (now - this.gazeAwayStart > 3500) {
          isGazeViolating = true;
          if (now - this.lastGazeAlert > 8000) {
            this._showToast("👀 Try to maintain eye contact with the camera.", "warning");
            this.lastGazeAlert = now;
          }
        }
      } else {
        if (this.gazeAwayStart && (now - this.gazeAwayStart > 3500)) {
          this.gazeAwayEvents.push({
            timestamp: new Date().toISOString(),
            duration_ms: now - this.gazeAwayStart
          });
        }
        this.gazeAwayStart = null;
      }
      
      if (this.prevLandmarks) {
        const movement = Math.abs(nose.x - this.prevLandmarks[1].x) + Math.abs(nose.y - this.prevLandmarks[1].y);
        this.postureVariances.push(movement);
        
        const mouthTop = landmarks[13];
        const mouthBottom = landmarks[14];
        const mouthOpening = Math.abs(mouthTop.y - mouthBottom.y);
        this.expressionVariances.push(mouthOpening);
      }
      this.prevLandmarks = landmarks;
      
      // Update Badge UI
      if (this.indicatorElement && this.totalFrames % 10 === 0) {
        if (isMultiFace) {
          this.indicatorElement.innerHTML = '<span class="badge bg-danger"><i class="bi bi-people-fill"></i> Multiple people detected</span>';
        } else if (isGazeViolating) {
          this.indicatorElement.innerHTML = '<span class="badge bg-warning text-dark"><i class="bi bi-eye-slash-fill"></i> Looking away</span>';
        } else {
          this.indicatorElement.innerHTML = '<span class="badge bg-success"><i class="bi bi-person-bounding-box"></i> Good tracking</span>';
        }
      }
    } else {
      if (this.gazeAwayStart && (now - this.gazeAwayStart > 3500)) {
        this.gazeAwayEvents.push({
          timestamp: new Date().toISOString(),
          duration_ms: now - this.gazeAwayStart
        });
      }
      this.gazeAwayStart = null;
      
      if (this.indicatorElement && this.totalFrames % 10 === 0) {
          this.indicatorElement.innerHTML = '<span class="badge bg-secondary"><i class="bi bi-exclamation-triangle"></i> Face lost</span>';
      }
    }
  }

  getMetrics() {
    if (this.totalFrames === 0 || !this.hasPermission) return null;
    
    const face_detected_pct = Math.round((this.framesWithFace / this.totalFrames) * 100);
    const eye_contact_pct = this.framesWithFace > 0 ? Math.round((this.framesWithEyeContact / this.framesWithFace) * 100) : 0;
    
    // Calculate average movement for posture (lower is more stable, we map to 0-100 score)
    let avgMovement = 0;
    if (this.postureVariances.length > 0) {
      avgMovement = this.postureVariances.reduce((a, b) => a + b, 0) / this.postureVariances.length;
    }
    // E.g., movement of 0.05 is quite jittery. We scale it so 0 movement = 100 score.
    const posture_score = Math.max(0, Math.min(100, 100 - (avgMovement * 2000)));
    
    // Calculate expression variety (variance of mouth opening)
    let expScore = 50;
    if (this.expressionVariances.length > 0) {
      const avgExp = this.expressionVariances.reduce((a, b) => a + b, 0) / this.expressionVariances.length;
      const variance = this.expressionVariances.reduce((a, b) => a + Math.pow(b - avgExp, 2), 0) / this.expressionVariances.length;
      // Scale variance to 0-100
      expScore = Math.min(100, Math.round(variance * 50000));
    }
    
    return {
      face_detected_pct: face_detected_pct,
      eye_contact_pct: eye_contact_pct,
      posture_score: Math.round(posture_score),
      expression_variety_score: expScore,
      gesture_activity_score: null, // Placeholder for MediaPipe Holistic
      face_count_violations_json: JSON.stringify(this.faceCountViolations),
      gaze_away_events_json: JSON.stringify(this.gazeAwayEvents)
    };
  }
}
window.WebcamAnalyzer = WebcamAnalyzer;
