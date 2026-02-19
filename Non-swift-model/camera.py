"""Webcam barcode scanning utility using OpenCV + pyzbar."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

import cv2

# Ensure pyzbar can locate libzbar on macOS Homebrew installs.
os.environ.setdefault("DYLD_FALLBACK_LIBRARY_PATH", "/opt/homebrew/lib:/usr/local/lib")

from pyzbar.pyzbar import decode


FrameCallback = Callable[[any], None]


@dataclass
class CameraScanResult:
    barcode: Optional[str]
    error: Optional[str]
    frames_seen: int


def find_first_readable_camera(indices: list[int]) -> Optional[int]:
    """Return the first camera index that can open and read at least one frame."""
    backend = cv2.CAP_AVFOUNDATION if os.name == "posix" else cv2.CAP_ANY
    for idx in indices:
        capture = cv2.VideoCapture(idx, backend)
        if not capture.isOpened():
            capture.release()
            continue
        ok, _ = capture.read()
        capture.release()
        if ok:
            return idx
    return None


def test_camera_access(camera_index: int = 0) -> tuple[bool, str]:
    """Quick probe for camera readability."""
    backend = cv2.CAP_AVFOUNDATION if os.name == "posix" else cv2.CAP_ANY
    capture = cv2.VideoCapture(camera_index, backend)
    if not capture.isOpened():
        capture.release()
        return (
            False,
            f"Camera index {camera_index} is unavailable. Try another index or check OS permissions.",
        )
    ok, _ = capture.read()
    capture.release()
    if not ok:
        return (
            False,
            f"Camera index {camera_index} opened but no frames were readable.",
        )
    return True, f"Camera index {camera_index} is accessible."


def scan_barcode_from_webcam(
    timeout_seconds: int = 15,
    camera_index: int = 0,
    on_frame: Optional[FrameCallback] = None,
) -> CameraScanResult:
    """Scan first visible barcode from webcam feed within timeout.

    Args:
        timeout_seconds: Maximum scan window.
        camera_index: OpenCV camera index.
        on_frame: Optional callback receiving BGR frames for live preview.
    """
    backend = cv2.CAP_AVFOUNDATION if os.name == "posix" else cv2.CAP_ANY
    capture = cv2.VideoCapture(camera_index, backend)
    if not capture.isOpened():
        capture.release()
        return CameraScanResult(
            barcode=None,
            error=f"Unable to open camera index {camera_index}.",
            frames_seen=0,
        )

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    start = time.time()
    found_barcode: Optional[str] = None
    frames_seen = 0

    try:
        while time.time() - start <= timeout_seconds:
            ok, frame = capture.read()
            if not ok:
                continue
            frames_seen += 1

            if on_frame is not None:
                on_frame(frame)

            decoded = decode(frame)
            if decoded:
                code = decoded[0].data.decode("utf-8").strip()
                if code:
                    found_barcode = code
                    break
    finally:
        capture.release()

    if found_barcode:
        return CameraScanResult(barcode=found_barcode, error=None, frames_seen=frames_seen)
    if frames_seen == 0:
        return CameraScanResult(
            barcode=None,
            error="Camera opened but no frames captured. Check camera permission for the terminal app.",
            frames_seen=0,
        )
    return CameraScanResult(
        barcode=None,
        error=f"No barcode detected within {timeout_seconds}s.",
        frames_seen=frames_seen,
    )
