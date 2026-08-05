"""
ONNX inference for the electrode-defect models on Jetson Orin.

Process:
    preprocess(image) -> grayscale, resize 512, normalize -> (1,1,512,512) float32
    infer(image)      -> runs all 5 models, returns a list of detected regions

The .onnx graphs already have sigmoid baked in, so each output is a [0,1] prob map.
Deps: numpy, opencv-python, onnxruntime-gpu (JetPack wheel).

    from infermodel import infer
    regions = infer(my_image)      # my_image: numpy array or path
"""
import os

import cv2
import numpy as np
import onnxruntime as ort # type: ignore

PATH = "inference/"
FEATURES = ["edge", "coating", "delam", "scratch", "crack"]

# albumentations A.Normalize(mean=0.485, std=0.229) over 0-255 pixels
MEAN = 0.485 * 255.0
STD = 0.229 * 255.0

# per-feature settings (mirror each <feature>/settings.py)
THRESH = {"edge": 0.9, "coating": 0.8, "delam": 0.9, "scratch": 0.3, "crack": 0.7}
MIN_AREA = {"edge": 1000, "coating": 1200, "delam": 10, "scratch": 1000, "crack": 800}

# CUDA runs the whole graph natively (cuDNN).
'''
TensorRT EP is dropped on purpose:
it can't build these UNet/ECNet pooling layers (addPoolingNd "windowSize" API error)
and just spams errors before falling back to CUDA anyway. Re-add it only after a
TRT-friendly re-export (export_onnx.py --static-batch) if you need the extra speed.
'''

PROVIDERS = ["CUDAExecutionProvider", "CPUExecutionProvider"] #use GPU if available, otherwise CPU

# Load all 5 ONNX models once, at import time.
SESSIONS = {
    f: ort.InferenceSession(os.path.join(PATH, f, "model.onnx"), providers=PROVIDERS)
    for f in FEATURES
}


def preprocess(image, size=512):
    """Grayscale -> resize size x size -> normalize -> (1,1,size,size) float32.

    'image' is a numpy array (2-D gray or 3-D BGR) or path.
    
    1. If 'image' is a string, treat it as a path and read the image.
    2. If 'image' is 3-D, convert to grayscale.
    3. Resize to (size, size) using linear interpolation.
    4. Normalize using MEAN and STD.
    5. Return a (1,1,size,size) float32 array.
    
    """
    if isinstance(image, str):
        path, image = image, cv2.imread(image, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"Cannot read image: {path}")
    
    if image.ndim == 3: #ndim is the number of dimensions of the array, if 3d bgr
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) #convert to grayscale
        
    resized = cv2.resize(image, (size, size), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    
    normed = (resized - MEAN) / STD #maps the 0-255 range to −2.1 … +2.2, centered on 0
    
    return normed[None, None, :, :].astype(np.float32)


def infer(image):
    """Run all 5 models on 'image'; return a list of detected regions.

    'image' is a numpy array (2-D gray or 3-D BGR); it is preprocessed before inference.
    'edge' is run first to get the electrode boundary, and every OTHER feature is
    clipped to inside the largest edge contour -- so all defects are reported only
    within the electrode edge. (Relies on FEATURES listing 'edge' first; if no edge
    is found, no defects are returned.)
    Each region: {feature, area, bbox [x,y,w,h], centroid [x,y], confidence,
    contour [[x,y], ...]}, with coordinates in the input image's pixel space.
    """
    h, w = image.shape[:2]
    tensor = preprocess(image)

    edge_mask = None
    regions = []
    for feat, sess in SESSIONS.items():
        name = sess.get_inputs()[0].name
        prob = np.squeeze(sess.run(None, {name: tensor})[0])  # sigmoid already baked in
        prob = cv2.resize(prob, (w, h), interpolation=cv2.INTER_LINEAR)
        binary = (prob > THRESH[feat]).astype(np.uint8)

        if feat == "edge":
            # filled mask of the largest edge contour; every other feature is confined to it
            edge_cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            edge_mask = np.zeros((h, w), np.uint8)
            if edge_cnts:
                cv2.drawContours(edge_mask, [max(edge_cnts, key=cv2.contourArea)], -1, 1, cv2.FILLED)
        else:
            binary &= edge_mask  # keep only defect pixels inside the electrode edge

        cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            area = cv2.contourArea(c)
            if area < MIN_AREA[feat]:
                continue
            m = cv2.moments(c)
            cx = int(m["m10"] / m["m00"]) if m["m00"] else 0
            cy = int(m["m01"] / m["m00"]) if m["m00"] else 0
            x, y, bw, bh = cv2.boundingRect(c)
            regions.append({
                "feature": feat,
                "area": float(area),
                "bbox": [x, y, bw, bh],
                "centroid": [cx, cy],
                "confidence": float(prob[cy, cx]),
                "contour": c.reshape(-1, 2).tolist(),
            })
    return regions

if __name__ == "__main__":
    testPATH = "testdata/test1614.jpg"

    image = cv2.imread(testPATH)                   # BGR, used for both inference and drawing
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {testPATH}")

    results = infer(image)                         # pass the array, not the path (infer needs .shape)
    print(f"{len(results)} region(s) detected")

    # draw the results on the image (the detected polygon, not a bounding box)
    for region in results:
        pts = np.array(region["contour"], np.int32).reshape(-1, 1, 2)
        cv2.polylines(image, [pts], True, (0, 255, 0), 2)   # outline the detected shape
        cx, cy = region["centroid"]
        cv2.circle(image, (cx, cy), 5, (0, 0, 255), -1)
        x, y = region["bbox"][:2]
        cv2.putText(image, f"{region['feature']} {region['confidence']:.2f}",
                    (x, max(y - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # save the annotated image first, so the result is kept even without a display
    output_path = "testdata/test1614_results.jpg"
    cv2.imwrite(output_path, image)
    print(f"saved -> {output_path}")

    # show it too, if a display is available (auto-skipped when headless / over SSH)
    try:
        cv2.imshow("Detected Regions", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error:
        pass
