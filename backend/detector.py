import cv2
import numpy as np
import os
import urllib.request

class ObjectDetector:
    def __init__(self, assets_dir: str = "assets", mode: str = "classification"):
        """
        Initializes the ObjectDetector with mode and asset directories.
        
        Args:
            assets_dir (str): Directory where model assets are saved.
            mode (str): Mode of execution - either "classification" (MobileNetV2) or "detection" (YOLOv8).
        """
        self.assets_dir = assets_dir
        self.mode = mode
        
        # Classification assets (MobileNetV2)
        self.model_path = os.path.join(self.assets_dir, "mobilenetv2-7.onnx")
        self.labels_path = os.path.join(self.assets_dir, "synset.txt")
        self.net_classifier = None
        self.classes = []
        
        # Object Detection assets (YOLOv8)
        self.yolo_path = os.path.join(self.assets_dir, "yolov8n.onnx")
        self.net_detector = None
        self.coco_classes = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", 
            "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", 
            "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", 
            "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", 
            "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", 
            "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", 
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", 
            "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", 
            "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", 
            "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
        ]

    def _download_assets(self):
        """Downloads the necessary model assets based on the active mode."""
        if not os.path.exists(self.assets_dir):
            os.makedirs(self.assets_dir, exist_ok=True)
            
        if self.mode == "classification":
            model_url = "https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx"
            fallback_model_url = "https://media.githubusercontent.com/media/onnx/models/main/validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx"
            labels_url = "https://raw.githubusercontent.com/onnx/models/main/validated/vision/classification/synset.txt"
            
            # Download labels
            if not os.path.exists(self.labels_path):
                print(f"Downloading labels from {labels_url}...")
                req = urllib.request.Request(labels_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(self.labels_path, 'wb') as f:
                    f.write(response.read())
                    
            # Download ONNX model
            if not os.path.exists(self.model_path):
                print(f"Downloading classification model from {model_url}...")
                try:
                    req = urllib.request.Request(model_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(self.model_path, 'wb') as f:
                        f.write(response.read())
                except Exception as e:
                    print(f"Failed download from GitHub raw, trying media CDN fallback: {e}")
                    req = urllib.request.Request(fallback_model_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(self.model_path, 'wb') as f:
                        f.write(response.read())
                print("Classification model download completed.")
                
        elif self.mode == "detection":
            yolo_url = "https://huggingface.co/Kalray/yolov8/resolve/main/yolov8n.onnx"
            fallback_yolo_url = "https://huggingface.co/Shad0ws/yolov8onnx/resolve/main/yolov8n.onnx"
            
            if not os.path.exists(self.yolo_path):
                print(f"Downloading YOLOv8 model from {yolo_url}...")
                try:
                    req = urllib.request.Request(yolo_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(self.yolo_path, 'wb') as f:
                        f.write(response.read())
                except Exception as e:
                    print(f"Failed download from primary YOLO URL, trying fallback: {e}")
                    req = urllib.request.Request(fallback_yolo_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(self.yolo_path, 'wb') as f:
                        f.write(response.read())
                print("YOLOv8 model download completed.")

    def load_model(self):
        """Loads the active mode's neural network into memory."""
        self._download_assets()
        
        if self.mode == "classification" and self.net_classifier is None:
            # Load classes
            with open(self.labels_path, "r") as f:
                self.classes = []
                for line in f.readlines():
                    line_str = line.strip()
                    if not line_str:
                        continue
                    if " " in line_str and line_str.split(" ", 1)[0].startswith("n") and len(line_str.split(" ", 1)[0]) == 9:
                        self.classes.append(line_str.split(" ", 1)[1])
                    else:
                        self.classes.append(line_str)
            
            # Load Network
            self.net_classifier = cv2.dnn.readNetFromONNX(self.model_path)
            
            # Warm up
            dummy_blob = np.zeros((1, 3, 224, 224), dtype=np.float32)
            self.net_classifier.setInput(dummy_blob)
            self.net_classifier.forward()
            
        elif self.mode == "detection" and self.net_detector is None:
            # Load Network
            self.net_detector = cv2.dnn.readNetFromONNX(self.yolo_path)
            
            # Warm up
            dummy_blob = np.zeros((1, 3, 640, 640), dtype=np.float32)
            self.net_detector.setInput(dummy_blob)
            self.net_detector.forward()

    def set_mode(self, mode: str):
        """Sets the execution mode (classification or detection) and ensures the model is loaded."""
        if mode not in ["classification", "detection"]:
            raise ValueError("Mode must be 'classification' or 'detection'")
        self.mode = mode
        self.load_model()

    def _preprocess_crop(self, crop: np.ndarray) -> np.ndarray:
        """Creates a normalized blob tensor for MobileNetV2 ONNX model."""
        blob = cv2.dnn.blobFromImage(
            crop, 
            scalefactor=1.0/255.0, 
            size=(224, 224), 
            mean=(0, 0, 0), 
            swapRB=True, 
            crop=False
        )
        blob[0, 0, :, :] = (blob[0, 0, :, :] - 0.485) / 0.229
        blob[0, 1, :, :] = (blob[0, 1, :, :] - 0.456) / 0.224
        blob[0, 2, :, :] = (blob[0, 2, :, :] - 0.406) / 0.225
        return blob

    def _get_candidate_rois(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Uses contour localization to identify ROIs (only for classification mode fallback)."""
        h_img, w_img, _ = image.shape
        img_area = h_img * w_img
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        v = np.median(blurred)
        sigma = 0.33
        lower = int(max(0, (1.0 - sigma) * v))
        upper = int(min(255, (1.0 + sigma) * v))
        edges = cv2.Canny(blurred, lower, upper)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        dilated = cv2.dilate(closed, kernel, iterations=1)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rois = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = w / float(h)
            if (0.01 * img_area < area < 0.90 * img_area) and (0.15 < aspect_ratio < 6.0):
                pad_x = int(w * 0.05)
                pad_y = int(h * 0.05)
                new_x = max(0, x - pad_x)
                new_y = max(0, y - pad_y)
                new_w = min(w_img - new_x, w + 2 * pad_x)
                new_h = min(h_img - new_y, h + 2 * pad_y)
                rois.append((new_x, new_y, new_w, new_h))
        rois = sorted(rois, key=lambda r: r[2] * r[3], reverse=True)
        return rois[:3]

    def detect_and_classify(self, image: np.ndarray, min_confidence: float = 0.20) -> list[dict]:
        """Runs the active model (Classification or Object Detection) on the image."""
        self.load_model()
        
        if self.mode == "classification":
            h_img, w_img, _ = image.shape
            rois = self._get_candidate_rois(image)
            rois.append((0, 0, w_img, h_img))
            
            detections = []
            seen_labels = set()
            
            for (x, y, w, h) in rois:
                crop = image[y:y+h, x:x+w]
                if crop.size == 0:
                    continue
                blob = self._preprocess_crop(crop)
                self.net_classifier.setInput(blob)
                preds = self.net_classifier.forward()
                
                exp_preds = np.exp(preds - np.max(preds))
                probabilities = exp_preds / np.sum(exp_preds)
                class_idx = np.argmax(probabilities)
                confidence = float(probabilities[0, class_idx])
                
                raw_label = self.classes[class_idx]
                clean_label = raw_label.split(',')[0].strip().title()
                
                if confidence >= min_confidence and clean_label not in seen_labels:
                    detections.append({
                        'label': clean_label,
                        'class_id': int(class_idx),
                        'confidence': confidence,
                        'box': (x, y, w, h)
                    })
                    seen_labels.add(clean_label)
            
            if len(detections) > 1:
                full_img_box = (0, 0, w_img, h_img)
                full_img_idx = next((i for i, d in enumerate(detections) if d['box'] == full_img_box), None)
                if full_img_idx is not None:
                    fallback_conf = detections[full_img_idx]['confidence']
                    has_better_sub = any(d['box'] != full_img_box and d['confidence'] > fallback_conf for d in detections)
                    if has_better_sub:
                        detections.pop(full_img_idx)
            return detections
            
        elif self.mode == "detection":
            h_img, w_img = image.shape[:2]
            
            # YOLOv8 expects input size 640x640, scaling by 1/255.0, swapping R and B channels
            blob = cv2.dnn.blobFromImage(
                image, 
                scalefactor=1.0/255.0, 
                size=(640, 640), 
                mean=(0, 0, 0), 
                swapRB=True, 
                crop=False
            )
            
            self.net_detector.setInput(blob)
            preds = self.net_detector.forward()  # Output shape: (1, 84, 8400)
            
            # Parse output
            preds = np.squeeze(preds)  # Shape becomes: (84, 8400)
            preds = preds.T            # Shape becomes: (8400, 84)
            
            boxes = []
            confidences = []
            class_ids = []
            
            # Scale coordinates back to original image size
            x_factor = w_img / 640.0
            y_factor = h_img / 640.0
            
            for row in preds:
                # Slices class confidence values (columns 4 to 83)
                classes_scores = row[4:]
                class_id = np.argmax(classes_scores)
                confidence = classes_scores[class_id]
                
                if confidence >= min_confidence:
                    x, y, w, h = row[0], row[1], row[2], row[3]
                    # Convert center coords to left-top corner coords
                    left = int((x - w / 2) * x_factor)
                    top = int((y - h / 2) * y_factor)
                    width = int(w * x_factor)
                    height = int(h * y_factor)
                    
                    boxes.append([left, top, width, height])
                    confidences.append(float(confidence))
                    class_ids.append(int(class_id))
            
            # Apply Non-Maximum Suppression (NMS) to eliminate redundant overlapping boxes
            indices = cv2.dnn.NMSBoxes(boxes, confidences, min_confidence, nms_threshold=0.45)
            
            detections = []
            if len(indices) > 0:
                # Flatten the index array safely
                flat_indices = indices.flatten() if isinstance(indices, np.ndarray) else [
                    i[0] if isinstance(i, (list, tuple, np.ndarray)) else i for i in indices
                ]
                
                for idx in flat_indices:
                    box = boxes[idx]
                    label = self.coco_classes[class_ids[idx]].replace('_', ' ').title()
                    detections.append({
                        'label': label,
                        'class_id': class_ids[idx],
                        'confidence': confidences[idx],
                        'box': (max(0, box[0]), max(max(0, box[1]), 0), max(1, box[2]), max(1, box[3]))
                    })
                    
            # Sort detections by confidence in descending order
            detections = sorted(detections, key=lambda d: d['confidence'], reverse=True)
            return detections

    def draw_detections(self, image: np.ndarray, detections: list[dict]) -> np.ndarray:
        """Draws bounding boxes, labels, and confidence metrics on the image canvas."""
        annotated = image.copy()
        
        # Color palette for drawings
        colors = [
            (255, 127, 0),   # Warm Orange
            (0, 200, 255),   # Neon Yellow
            (255, 0, 127),   # Pink
            (46, 204, 113),  # Emerald Green
            (155, 89, 182),  # Amethyst Purple
            (241, 196, 15)   # Amber Gold
        ]
        
        for idx, det in enumerate(detections):
            x, y, w, h = det['box']
            label = det['label']
            confidence = det['confidence']
            
            # Alternate colors dynamically
            box_color = colors[idx % len(colors)]
            text_color = (255, 255, 255)
            
            thickness = max(2, int(min(image.shape[0], image.shape[1]) * 0.005))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), box_color, thickness)
            
            caption = f"{label} ({confidence:.0%})"
            font_scale = max(0.45, min(w, h) / 350.0)
            font_thickness = max(1, int(font_scale * 1.8))
            
            (text_w, text_h), baseline = cv2.getTextSize(
                caption, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
            )
            
            box_y1 = max(0, y - text_h - 10)
            box_y2 = y
            box_x1 = x
            box_x2 = min(image.shape[1], x + text_w + 10)
            
            cv2.rectangle(annotated, (box_x1, box_y1), (box_x2, box_y2), box_color, cv2.FILLED)
            
            text_y = y - 5 if y - text_h - 10 >= 0 else y + text_h + 5
            cv2.putText(
                annotated,
                caption,
                (x + 5, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                text_color,
                font_thickness,
                lineType=cv2.LINE_AA
            )
            
        return annotated
