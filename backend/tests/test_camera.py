import cv2
import numpy as np

from aristote.hardware.camera import MockCamera, deskew_page, enhance_for_ocr, order_corners, synthetic_page


def test_order_corners():
    pts = np.array([[10, 90], [90, 10], [10, 10], [90, 90]])
    assert order_corners(pts).tolist() == [[10, 10], [90, 10], [90, 90], [10, 90]]


def test_tilted_page_is_found_and_flattened():
    image = synthetic_page()
    flat, found = deskew_page(image)
    assert found
    h, w = flat.shape[:2]
    assert 1.15 < h / w < 1.4  # format portrait de la feuille simulée (800 × 1020)
    # Après redressement, l'image est presque entièrement blanche (le bureau sombre a disparu).
    assert np.mean(cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY)) > 200


def test_no_page_returns_original():
    image = np.full((400, 600, 3), 80, dtype=np.uint8)
    out, found = deskew_page(image)
    assert not found and out is image


def test_mock_camera_produces_jpeg():
    result = MockCamera().capture()
    assert result.page_found and result.jpeg[:2] == b"\xff\xd8"
    assert enhance_for_ocr(result.image).ndim == 2
