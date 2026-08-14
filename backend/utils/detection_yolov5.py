"""
Simple License Plate Pipeline
 - YOLOv5 detects regions (default yolov5m, fallback yolov5s)
 - EasyOCR reads text from the best crop
 - App checks if plate exists in DB (exact match after normalization)
"""

import os
import re
import cv2
import base64
import logging
import numpy as np
import torch
import easyocr

# Official YOLOv5 pip package
import sys

# Prefer official yolov5 package APIs; fall back to local repo if needed
_here = os.path.dirname(__file__)
_local_yolov5_dir = os.path.join(_here, 'yolov5')

try:
    # First, try the pip package layout
    from yolov5.models.common import DetectMultiBackend
    from yolov5.utils.general import non_max_suppression, scale_boxes
    from yolov5.utils.torch_utils import select_device
    from yolov5.utils.augmentations import letterbox
    _Y5_IMPORT_SOURCE = 'pip'
except Exception:
    # Fall back to the bundled yolov5 repo in backend/yolov5
    if _local_yolov5_dir not in sys.path:
        sys.path.insert(0, _local_yolov5_dir)
    from models.common import DetectMultiBackend
    from utils.general import non_max_suppression, scale_boxes
    from utils.torch_utils import select_device
    from utils.augmentations import letterbox
    _Y5_IMPORT_SOURCE = 'local'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LicensePlateDetector:
    """Detect and extract license plates using YOLOv5 + EasyOCR (minimal)."""

    def __init__(self):
        logger.info("Initializing License Plate Detector...")

        # Device via yolov5 helpers
        self.device = select_device('')  # auto (CUDA if available)

        # Determine weights (simple):
        # Priority: ENV YOLOV5_WEIGHTS -> yolov5m.pt -> yolov5s.pt
        env_w = os.getenv('YOLOV5_WEIGHTS')
        candidate_weights = []
        if env_w and os.path.exists(env_w):
            candidate_weights.append(env_w)
        # Prefer yolov5m if available (auto-download if online)
        candidate_weights.append('yolov5m.pt')
        candidate_weights.append('yolov5s.pt')  # fallback (auto-download)

        weights_used = None
        last_err = None
        for w in candidate_weights:
            try:
                logger.info(f"Loading YOLOv5 weights: {w} (source={_Y5_IMPORT_SOURCE})")
                self.model = DetectMultiBackend(w, device=self.device, dnn=False, fp16=False)
                weights_used = w
                break
            except Exception as e:
                last_err = e
                logger.warning(f"Failed to load weights '{w}': {e}")

        if weights_used is None:
            raise RuntimeError(f"Could not load any YOLOv5 weights. Last error: {last_err}")

        # Inference params
        self.img_size = int(os.getenv('YOLOV5_IMG_SIZE', '640'))
        self.conf_thres = float(os.getenv('YOLOV5_CONF', '0.25'))
        self.iou_thres = float(os.getenv('YOLOV5_IOU', '0.45'))
        self.names = self.model.names
        self.stride = self.model.stride
        self.pt = self.model.pt
        logger.info(f"YOLOv5 model loaded on {self.device}")

        # EasyOCR (allow region/language customization)
        self.region = os.getenv('PLATE_REGION', '').lower()  # e.g., 'dz' for Algeria
        langs_env = os.getenv('PLATE_OCR_LANGS', 'en,ar' if self.region == 'dz' else 'en')
        langs = [s.strip() for s in langs_env.split(',') if s.strip()]
        # EasyOCR constraint: Arabic-compatible group is limited
        if 'ar' in langs:
            allowed = {'ar', 'fa', 'ur', 'ug', 'en'}
            langs = [l for l in langs if l in allowed]
            if 'en' not in langs:
                langs.append('en')
        try:
            self.reader = easyocr.Reader(langs, gpu=False)
            logger.info(f"EasyOCR initialized successfully (langs={langs})")
        except Exception as e:
            logger.warning(f"EasyOCR init failed for langs={langs} ({e}); falling back to ['en']")
            self.reader = easyocr.Reader(['en'], gpu=False)

        # Minimal heuristic config for selecting plate-like boxes
        self.min_area = int(os.getenv('PLATE_MIN_AREA', '1000'))
        # Algeria plates can be longer; widen default AR band slightly when region is DZ
        default_min_ar = '1.8' if self.region == 'dz' else '2.0'
        default_max_ar = '8.0' if self.region == 'dz' else '6.0'
        self.min_ar = float(os.getenv('PLATE_MIN_AR', default_min_ar))  # width/height
        self.max_ar = float(os.getenv('PLATE_MAX_AR', default_max_ar))

        # Plate class IDs detection (so we can filter by class id, not label text)
        # Auto-detect classes containing keywords; allow override via env
        plate_name_keywords = [s.strip().lower() for s in os.getenv('PLATE_CLASS_KEYWORDS', 'plate,license,licence,lp').split(',') if s.strip()]
        explicit_classes_env = os.getenv('YOLOV5_PLATE_CLASSES')  # e.g. "0,1" or "plate,license"

        plate_ids = []
        if explicit_classes_env:
            items = [s.strip() for s in explicit_classes_env.split(',') if s.strip()]
            for it in items:
                if it.isdigit():
                    plate_ids.append(int(it))
                else:
                    # map name to id if present
                    for i, n in enumerate(self.names):
                        if isinstance(n, str) and n.lower() == it.lower():
                            plate_ids.append(i)
                            break
        else:
            # auto-detect by keywords
            for i, n in enumerate(self.names):
                if isinstance(n, str):
                    nl = n.lower()
                    if any(k in nl for k in plate_name_keywords):
                        plate_ids.append(i)

        # Deduplicate and sort
        self.plate_class_ids = sorted(set(plate_ids)) if plate_ids else []
        if self.plate_class_ids:
            logger.info(f"Plate class IDs: {self.plate_class_ids} -> {[self.names[i] for i in self.plate_class_ids]}")
        else:
            logger.info("No explicit plate class IDs detected; will fall back to shape heuristics")

    # -------------------- OCR helpers --------------------
    def preprocess_plate(self, plate_img):
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, 11, 17, 17)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        thresh = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        return thresh

    def extract_text_from_plate(self, plate_img):
        """Run OCR on cropped plate image (preprocessed, then fallback to original)."""
        try:
            processed = self.preprocess_plate(plate_img)
            results = self.reader.readtext(processed, detail=1, paragraph=False)
            if not results:
                results = self.reader.readtext(plate_img, detail=1, paragraph=False)
            if not results:
                return None

            # Take the highest-confidence line rather than concatenating all
            best = max(results, key=lambda r: r[2] if len(r) > 2 else 0)
            return best[1] if best else None
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None

    def _normalize_arabic_indic_digits(self, s: str) -> str:
        """Convert Arabic-Indic digits to ASCII 0-9."""
        arabic_to_ascii = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        eastern_to_ascii = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')  # Persian/Eastern Arabic
        return s.translate(arabic_to_ascii).translate(eastern_to_ascii)

    def clean_plate_text(self, text):
        if not text:
            return ""
        # Normalize digits from Arabic-Indic to ASCII first (helps for DZ plates)
        t = self._normalize_arabic_indic_digits(str(text))
        t = t.upper()
        if self.region == 'dz':
            # DZ: keep only digits; drop letters and symbols
            t = re.sub(r'[^0-9]', '', t)
            return t
        # Default: alnum plus space/dash, with common OCR corrections
        t = re.sub(r'[^A-Za-z0-9\s\-]', '', t)
        t = t.replace('O', '0').replace('I', '1').replace('S', '5').replace('Z', '2')
        t = ' '.join(t.split())
        return t.strip()

    def is_valid_plate_format(self, text):
        t = text.replace(' ', '').replace('-', '')
        # Algeria: plates are numeric only
        if self.region == 'dz':
            if not t.isdigit():
                return False
            # Typical length range; make adjustable by env
            min_len = int(os.getenv('DZ_MIN_LEN', '5'))
            max_len = int(os.getenv('DZ_MAX_LEN', '12'))
            return min_len <= len(t) <= max_len

        # Default formats
        if len(t) < 4 or len(t) > 10:
            return False
        has_letter = bool(re.search(r'[A-Z]', text))
        has_number = bool(re.search(r'[0-9]', text))
        if len(t) >= 5 and t.isdigit():
            return True
        if not (has_letter and has_number):
            return False
        patterns = [
            r'^[A-Z]{2,3}[0-9]{3,6}$',
            r'^[0-9]{3,6}[A-Z]{2,3}$',
            r'^[A-Z]{1,2}[0-9]{2,5}[A-Z]{1,2}$',
            r'^[0-9]{5,9}$',
        ]
        return any(re.match(p, t) for p in patterns)

    # -------------------- YOLO helpers --------------------
    def detect_plate_region(self, image_path):
        """Return list of (plate_crop, confidence, bbox) from the image."""
        try:
            img_bgr = cv2.imread(image_path)
            if img_bgr is None:
                raise ValueError(f"Could not read image from {image_path}")
            # Prepare letterboxed input
            img = letterbox(img_bgr, self.img_size, stride=self.stride, auto=self.pt)[0]
            img = img.transpose((2, 0, 1))[::-1]  # HWC->CHW, BGR->RGB
            img = np.ascontiguousarray(img)
            img = torch.from_numpy(img).to(self.device)
            img = img.float() / 255.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            # Inference
            pred = self.model(img, augment=False, visualize=False)
            # NMS (restrict to plate classes when available)
            classes_filter = self.plate_class_ids if getattr(self, 'plate_class_ids', None) else None
            pred = non_max_suppression(
                pred,
                self.conf_thres,
                self.iou_thres,
                classes=classes_filter,
                agnostic=False,
                max_det=300,
            )

            crops = []
            for det in pred:
                if len(det):
                    det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], img_bgr.shape).round()
                    # Log detected class IDs and names for debugging
                    try:
                        classes_in_det = sorted(set(int(c) for c in det[:, 5].tolist()))
                        names_in_det = [self.names[c] if c < len(self.names) else str(c) for c in classes_in_det]
                        logger.info(f"YOLO found {len(det)} objects; classes: {classes_in_det} -> {names_in_det}")
                    except Exception:
                        logger.info(f"YOLO found {len(det)} objects in image")

                    for *xyxy, conf, cls in det.tolist():
                        x1, y1, x2, y2 = map(int, xyxy)
                        confidence = float(conf)
                        # Apply shape heuristic only if we didn't filter by class
                        if not classes_filter:
                            w, h = max(0, x2 - x1), max(0, y2 - y1)
                            area = w * h
                            ar = (w / h) if h > 0 else 0
                            if area < self.min_area or not (self.min_ar <= ar <= self.max_ar):
                                continue
                        padding = 20 if self.region == 'dz' else 12
                        px1 = max(0, x1 - padding)
                        py1 = max(0, y1 - padding)
                        px2 = min(img_bgr.shape[1], x2 + padding)
                        py2 = min(img_bgr.shape[0], y2 + padding)
                        crop = img_bgr[py1:py2, px1:px2]
                        if crop.size > 0:
                            crops.append((crop, confidence, (x1, y1, x2, y2)))
            return crops
        except Exception as e:
            logger.error(f"Error in plate detection: {e}")
            return []

    # -------------------- Public APIs --------------------
    def detect_and_extract(self, image_path):
        """Return list of detected license plate texts from an image."""
        try:
            crops = self.detect_plate_region(image_path)
            if not crops:
                # Fallback: OCR on entire image (simple)
                img = cv2.imread(image_path)
                if img is None:
                    return []
                text = self.extract_text_from_plate(img)
                if not text:
                    return []
                cleaned = self.clean_plate_text(text)
                return [cleaned] if self.is_valid_plate_format(cleaned) else []

            detected = []
            for plate_img, conf, _bbox in crops:
                text = self.extract_text_from_plate(plate_img)
                if not text:
                    continue
                cleaned = self.clean_plate_text(text)
                if self.is_valid_plate_format(cleaned):
                    detected.append(cleaned)

            # Deduplicate preserving order
            seen = set()
            unique = []
            for p in detected:
                if p not in seen:
                    seen.add(p)
                    unique.append(p)
            return unique
        except Exception as e:
            logger.error(f"Error in detect_and_extract: {e}")
            return []

    def normalize_plate(self, p):
        if p is None:
            return ''
        s = str(p).upper().strip().replace(' ', '').replace('-', '')
        if getattr(self, 'region', '') == 'dz':
            # Keep only digits for DZ
            s = re.sub(r'[^0-9]', '', s)
        return s

    def is_exact_match(self, detected_plate, database_plates):
        dp = self.normalize_plate(detected_plate)
        for db in database_plates:
            if dp == self.normalize_plate(db):
                return db
        return None

    def detect_and_annotate(self, image_path, database_plates_dict):
        """Detect plates, annotate image (green=known, red=unknown), return JSON dict."""
        try:
            img_bgr = cv2.imread(image_path)
            if img_bgr is None:
                raise ValueError(f"Could not read image from {image_path}")
            img_annotated = img_bgr.copy()

            crops = self.detect_plate_region(image_path)
            results = []

            for plate_img, conf, bbox in crops:
                x1, y1, x2, y2 = bbox
                text = self.extract_text_from_plate(plate_img)
                if not text:
                    continue
                cleaned = self.clean_plate_text(text)
                if not self.is_valid_plate_format(cleaned):
                    continue

                matched_plate = self.is_exact_match(cleaned, list(database_plates_dict.keys()))
                matched_info = database_plates_dict.get(matched_plate) if matched_plate else None
                is_known = matched_plate is not None
                color = (0, 255, 0) if is_known else (0, 0, 255)
                label_bg = (0, 200, 0) if is_known else (0, 0, 200)

                # Draw bbox
                cv2.rectangle(img_annotated, (x1, y1), (x2, y2), color, 3)

                # Text label
                label = f"{matched_info.get('name')} - {matched_plate}" if (is_known and matched_info) else cleaned
                font = cv2.FONT_HERSHEY_SIMPLEX
                (tw, th), bl = cv2.getTextSize(label, font, 0.7, 2)
                ly = y1 - 10 if y1 - 10 > th else y1 + th + 10
                cv2.rectangle(img_annotated, (x1, ly - th - 5), (x1 + tw + 10, ly + bl + 5), label_bg, -1)
                cv2.putText(img_annotated, label, (x1 + 5, ly), font, 0.7, (255, 255, 255), 2)

                # Status badge
                status_text = "REGISTERED" if is_known else "UNKNOWN"
                (sw, sh), _ = cv2.getTextSize(status_text, font, 0.5, 1)
                cv2.rectangle(img_annotated, (x2 - sw - 15, y1 + 5), (x2 - 5, y1 + sh + 15), label_bg, -1)
                cv2.putText(img_annotated, status_text, (x2 - sw - 10, y1 + sh + 10), font, 0.5, (255, 255, 255), 1)

                result = {
                    'detected_plate': cleaned,
                    'confidence': float(conf),
                    'bbox': (x1, y1, x2, y2),
                }
                if is_known and matched_info:
                    result.update({
                        'status': 'known_user',
                        'license_plate': matched_plate,
                        'name': matched_info.get('name'),
                        'user_id': matched_info.get('id'),
                    })
                else:
                    result.update({
                        'status': 'unknown_user',
                        'license_plate': cleaned,
                    })
                results.append(result)

            # Fallback: OCR on full image when no crops
            if not results:
                logger.info("No detections from YOLO, trying OCR on full image...")
                text = self.extract_text_from_plate(img_bgr)
                if text:
                    cleaned = self.clean_plate_text(text)
                    if self.is_valid_plate_format(cleaned):
                        matched_plate = self.is_exact_match(cleaned, list(database_plates_dict.keys()))
                        matched_info = database_plates_dict.get(matched_plate) if matched_plate else None
                        is_known = matched_plate is not None
                        color = (0, 255, 0) if is_known else (0, 0, 255)
                        cv2.putText(img_annotated, f"{cleaned} (Full OCR)", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
                        result = {
                            'detected_plate': cleaned,
                            'confidence': 0.5,
                            'status': 'known_user' if is_known else 'unknown_user',
                            'license_plate': matched_plate if is_known else cleaned,
                        }
                        if is_known and matched_info:
                            result.update({'name': matched_info.get('name'), 'user_id': matched_info.get('id')})
                        results.append(result)

            # Encode annotated image
            ok, buf = cv2.imencode('.jpg', img_annotated)
            img_b64 = base64.b64encode(buf).decode('utf-8') if ok else ''

            if results:
                best = max(results, key=lambda r: r.get('confidence', 0))
                best.pop('bbox', None)
                best['annotated_image_base64'] = img_b64
                logger.info(f"Detection complete: {best['status']}")
                return best
            else:
                logger.info("No valid license plates detected")
                return {
                    'status': 'no_plate_found',
                    'annotated_image_base64': img_b64,
                    'message': 'No license plate detected in the image'
                }
        except Exception as e:
            logger.error(f"Error in detect_and_annotate: {e}")
            return {'status': 'error', 'message': str(e)}
