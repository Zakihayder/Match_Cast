"""
╔══════════════════════════════════════════════════════════════╗
║        MatchCast AI — YOLOv8 Fine-Tuning (Google Colab)     ║
╚══════════════════════════════════════════════════════════════╝

INSTRUCTIONS:
  1. Open Google Colab → https://colab.research.google.com
  2. Runtime → Change runtime type → T4 GPU (or better)
  3. Copy EACH SECTION below into a SEPARATE Colab cell
  4. Run cells in order (1 → 2 → 3 → 4 → 5)
  5. Download best.pt at the end
  6. Place it in your repo: data/models/best.pt

DATASET: Roboflow "Football Players Detection"
  - Classes: player, ball, referee, goalkeeper
  - ~1000+ annotated images
  - Pre-formatted for YOLOv8

EXPECTED TIME: ~20-30 min on T4 GPU
"""


# ════════════════════════════════════════════════════════════
# CELL 1: Install dependencies
# ════════════════════════════════════════════════════════════

# !pip install -q ultralytics roboflow


# ════════════════════════════════════════════════════════════
# CELL 2: Download football dataset from Roboflow
# ════════════════════════════════════════════════════════════

# --- OPTION A: Using Roboflow API (recommended) ---
# Get a free API key at https://app.roboflow.com → Settings → API Key

"""
from roboflow import Roboflow

# ⚠️ Replace with your actual Roboflow API key
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")

# Dataset: "Football Players Detection" (player, ball, referee, goalkeeper)
# URL: https://universe.roboflow.com/roboflow-jvuqo/football-players-detection-3zvbc
project = rf.workspace("roboflow-jvuqo").project("football-players-detection-3zvbc")
version = project.version(14)  # Use latest version number
dataset = version.download("yolov8")

DATA_YAML = dataset.location + "/data.yaml"
print(f"✅ Dataset downloaded to: {dataset.location}")
print(f"✅ data.yaml path: {DATA_YAML}")
"""

# --- OPTION B: Alternative larger dataset ---
# URL: https://universe.roboflow.com/yolo-tutorials/football-player-detection-jrib0
"""
project = rf.workspace("yolo-tutorials").project("football-player-detection-jrib0")
version = project.version(1)
dataset = version.download("yolov8")
DATA_YAML = dataset.location + "/data.yaml"
"""


# ════════════════════════════════════════════════════════════
# CELL 3: Fine-tune YOLOv8
# ════════════════════════════════════════════════════════════

"""
from ultralytics import YOLO

# Start from pretrained yolov8n (nano) — fastest to train
# Upgrade to yolov8s.pt (small) or yolov8m.pt (medium) if
# you have time and want better accuracy
model = YOLO("yolov8n.pt")

# Fine-tune on football dataset
results = model.train(
    data=DATA_YAML,
    epochs=50,         # 50 is a good start; increase to 80-100 if val loss is still dropping
    imgsz=640,         # Standard size — increase to 1280 for better ball detection (slower)
    batch=16,          # Reduce to 8 if you get OOM errors
    device=0,          # GPU
    patience=10,       # Stop early if no improvement for 10 epochs
    save=True,         # Save checkpoints
    project="matchcast",
    name="football_v1",
    verbose=True,
    # Performance tuning
    lr0=0.01,          # Initial learning rate
    lrf=0.01,          # Final learning rate factor
    mosaic=1.0,        # Mosaic augmentation (good for multi-object scenes)
    close_mosaic=10,   # Disable mosaic for last 10 epochs
)

print("\\n" + "="*60)
print("✅ TRAINING COMPLETE")
print(f"Best weights: matchcast/football_v1/weights/best.pt")
print(f"Last weights: matchcast/football_v1/weights/last.pt")
print("="*60)
"""


# ════════════════════════════════════════════════════════════
# CELL 4: VISUAL VALIDATION (⚠️ DO NOT SKIP THIS)
# ════════════════════════════════════════════════════════════

"""
from ultralytics import YOLO
import cv2
from google.colab.patches import cv2_imshow
import glob

# Load the fine-tuned model
model = YOLO("matchcast/football_v1/weights/best.pt")

# Check what classes the model learned
print(f"Model classes: {model.names}")
print(f"Number of classes: {len(model.names)}")

# --- Test on validation images ---
# Grab a few validation images to visually check
val_images = glob.glob(f"{dataset.location}/valid/images/*.jpg")[:5]

if not val_images:
    val_images = glob.glob(f"{dataset.location}/test/images/*.jpg")[:5]

print(f"\\nTesting on {len(val_images)} images...")

for img_path in val_images:
    print(f"\\n--- {img_path} ---")
    results = model(img_path, conf=0.3)
    
    for r in results:
        annotated = r.plot()
        cv2_imshow(annotated)
        
        # Count detections by class
        if len(r.boxes) > 0:
            for cls_id in r.boxes.cls.unique():
                cls_name = model.names[int(cls_id)]
                count = (r.boxes.cls == cls_id).sum().item()
                print(f"  {cls_name}: {int(count)} detected")
        else:
            print("  ⚠️ No detections!")

# --- Metrics summary ---
print("\\n" + "="*60)
print("VALIDATION METRICS")
metrics = model.val()
print(f"  mAP50:     {metrics.box.map50:.3f}")
print(f"  mAP50-95:  {metrics.box.map:.3f}")
print(f"  Precision: {metrics.box.mp:.3f}")
print(f"  Recall:    {metrics.box.mr:.3f}")
print("="*60)

print("\\n⚠️ VISUAL CHECK:")
print("  1. Are players correctly boxed?")
print("  2. Is the ball detected (it's small — might have lower confidence)?")
print("  3. Are referees distinguished from players?")
print("  4. Any major false positives (crowd, ads, etc.)?")
"""


# ════════════════════════════════════════════════════════════
# CELL 5: Download best.pt
# ════════════════════════════════════════════════════════════

"""
from google.colab import files

# Download the fine-tuned weights
files.download("matchcast/football_v1/weights/best.pt")

print("\\n✅ Downloaded best.pt")
print("\\nNEXT STEPS:")
print("  1. Place best.pt in your repo at: data/models/best.pt")
print("  2. The backend will auto-detect and use it")
print("  3. Tell Antigravity you're ready for Phase 1.1 visual validation")
"""


# ════════════════════════════════════════════════════════════
# BONUS: Test on YOUR match video (optional but recommended)
# ════════════════════════════════════════════════════════════

"""
# Upload a frame from your actual match video to Colab first:
# from google.colab import files
# uploaded = files.upload()  # Select a frame screenshot

from ultralytics import YOLO
from google.colab.patches import cv2_imshow

model = YOLO("matchcast/football_v1/weights/best.pt")

# Replace with your uploaded file name
results = model("your_match_frame.jpg", conf=0.25)

for r in results:
    annotated = r.plot()
    cv2_imshow(annotated)
    print(f"Total detections: {len(r.boxes)}")
    for cls_id in r.boxes.cls.unique():
        cls_name = model.names[int(cls_id)]
        count = (r.boxes.cls == cls_id).sum().item()
        print(f"  {cls_name}: {int(count)}")
"""
