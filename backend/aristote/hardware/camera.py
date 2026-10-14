"""Caméra de scan des copies.

- `Picamera2Camera` : Raspberry Pi Camera Module 3 (autofocus déclenché avant chaque capture).
- `OpenCVCamera` : webcam USB (mini-PC).
- `MockCamera` : page synthétique (développement, tests).

Après la capture, `deskew_page()` cherche le contour de la feuille et la remet à plat (vue de dessus),
ce qui améliore nettement l'OCR quand la copie est posée de travers.
"""

from __future__ import annotations

import threading

import cv2
import numpy as np

from .base import CaptureResult

JPEG_QUALITY = 90
PREVIEW_WIDTH = 960


# --- Traitement d'image ---------------------------------------------------------------------------

def order_corners(pts: np.ndarray) -> np.ndarray:
    """Ordonne 4 points : haut-gauche, haut-droit, bas-droit, bas-gauche."""
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()  # y - x
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
                    dtype=np.float32)


def find_page_quad(image: np.ndarray, min_area_ratio: float = 0.2) -> np.ndarray | None:
    """Renvoie les 4 coins de la feuille (ordonnés) ou None si aucune feuille n'est détectée."""
    h, w = image.shape[:2]
    scale = 1000 / max(h, w)
    small = cv2.resize(image, (int(w * scale), int(h * scale))) if scale < 1 else image
    scale = min(scale, 1.0)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if small.ndim == 3 else small
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = min_area_ratio * small.shape[0] * small.shape[1]
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        if cv2.contourArea(contour) < min_area:
            break
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return order_corners(approx / scale)
    return None


def warp_page(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    tl, tr, br, bl = corners
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(corners, target)
    return cv2.warpPerspective(image, matrix, (width, height))


def deskew_page(image: np.ndarray) -> tuple[np.ndarray, bool]:
    corners = find_page_quad(image)
    if corners is None:
        return image, False
    return warp_page(image, corners), True


def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
    """Niveaux de gris + égalisation locale du contraste (CLAHE) : robuste aux ombres de la potence."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)


def encode_jpeg(image: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("échec de l'encodage JPEG")
    return buf.tobytes()


def _resize_width(image: np.ndarray, width: int) -> np.ndarray:
    h, w = image.shape[:2]
    if w <= width:
        return image
    return cv2.resize(image, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)


def _result(image: np.ndarray, deskew: bool) -> CaptureResult:
    found = False
    if deskew:
        image, found = deskew_page(image)
    return CaptureResult(image=image, jpeg=encode_jpeg(image), page_found=found)


# --- Implémentations ------------------------------------------------------------------------------

class Picamera2Camera:
    def __init__(self, width: int, height: int, deskew: bool = True) -> None:
        from picamera2 import Picamera2  # paquet apt python3-picamera2
        from libcamera import controls

        self._deskew = deskew
        self._lock = threading.Lock()
        self._cam = Picamera2()
        self._controls = controls
        # Flux principal pleine résolution pour le scan, flux « lores » pour l'aperçu à l'écran.
        self._config = self._cam.create_still_configuration(
            main={"size": (width, height), "format": "RGB888"},
            lores={"size": (PREVIEW_WIDTH, PREVIEW_WIDTH * height // width), "format": "YUV420"},
            display=None,
        )
        self._cam.configure(self._config)
        self._cam.start()
        self._cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})

    def capture(self) -> CaptureResult:
        with self._lock:
            self._cam.set_controls({"AfMode": self._controls.AfModeEnum.Auto})
            self._cam.autofocus_cycle()
            # Picamera2 "RGB888" renvoie un tableau dans l'ordre BGR, directement utilisable par OpenCV.
            frame = self._cam.capture_array("main")
            self._cam.set_controls({"AfMode": self._controls.AfModeEnum.Continuous})
        return _result(frame, self._deskew)

    def preview_jpeg(self) -> bytes:
        with self._lock:
            yuv = self._cam.capture_array("lores")
        bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV420p2BGR)
        return encode_jpeg(bgr, quality=70)

    def close(self) -> None:
        self._cam.stop()
        self._cam.close()


class OpenCVCamera:
    def __init__(self, device: int, width: int, height: int, deskew: bool = True) -> None:
        self._deskew = deskew
        self._lock = threading.Lock()
        self._cap = cv2.VideoCapture(device)
        if not self._cap.isOpened():
            raise RuntimeError(f"webcam {device} introuvable")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def _read(self) -> np.ndarray:
        with self._lock:
            for _ in range(3):  # vide les images en attente pour obtenir une image fraîche
                self._cap.grab()
            ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("lecture de la webcam impossible")
        return frame

    def capture(self) -> CaptureResult:
        return _result(self._read(), self._deskew)

    def preview_jpeg(self) -> bytes:
        return encode_jpeg(_resize_width(self._read(), PREVIEW_WIDTH), quality=70)

    def close(self) -> None:
        self._cap.release()


def synthetic_page(width: int = 1600, height: int = 1200, text: str = "1/3 + 1/4 = 2/7") -> np.ndarray:
    """Feuille blanche inclinée sur un bureau sombre, avec une ligne de texte."""
    desk = np.full((height, width, 3), (60, 45, 35), dtype=np.uint8)
    page_w, page_h = int(width * 0.5), int(width * 0.5 * 1.414)
    page_h = min(page_h, int(height * 0.85))
    page = np.full((page_h, page_w, 3), 245, dtype=np.uint8)
    cv2.putText(page, text, (40, page_h // 3), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (20, 20, 20), 3, cv2.LINE_AA)
    src = np.array([[0, 0], [page_w, 0], [page_w, page_h], [0, page_h]], dtype=np.float32)
    cx, cy = width / 2, height / 2
    angle = np.deg2rad(8)
    rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    dst = (src - [page_w / 2, page_h / 2]) @ rot.T + [cx, cy]
    matrix = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
    warped = cv2.warpPerspective(page, matrix, (width, height))
    mask = cv2.warpPerspective(np.full((page_h, page_w), 255, np.uint8), matrix, (width, height))
    desk[mask > 0] = warped[mask > 0]
    return desk


class MockCamera:
    def __init__(self, deskew: bool = True, image: np.ndarray | None = None) -> None:
        self._deskew = deskew
        self._image = image if image is not None else synthetic_page()

    def capture(self) -> CaptureResult:
        return _result(self._image.copy(), self._deskew)

    def preview_jpeg(self) -> bytes:
        return encode_jpeg(_resize_width(self._image, PREVIEW_WIDTH), quality=70)

    def close(self) -> None:
        pass
