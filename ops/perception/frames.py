"""Frame sources for detection: a video file, a folder of images, or a single image (OpenCV).

Yields (index, t_seconds, RGB uint8 frame). For image folders t = index / fps.
"""
from pathlib import Path

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def iter_frames(src, fps: float = 10.0, every: int = 1, start_t: float = 0.0):
    import cv2
    p = Path(src)
    if p.is_dir() or p.suffix.lower() in IMAGE_EXT:
        files = sorted(f for f in (p.iterdir() if p.is_dir() else [p]) if f.suffix.lower() in IMAGE_EXT)
        for i, f in enumerate(files):
            if i % every == 0:
                img = cv2.imread(str(f))
                if img is not None:
                    yield i, start_t+i/fps, cv2.cvtColor(img, cv2.COLOR_BGR2RGB), f.name
        return
    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        raise FileNotFoundError(f'cannot open video {p}')
    vfps = cap.get(cv2.CAP_PROP_FPS) or fps
    i = 0
    try:
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if i % every == 0:
                yield i, start_t+i/vfps, cv2.cvtColor(img, cv2.COLOR_BGR2RGB), f'{p.name}#{i}'
            i += 1
    finally:
        cap.release()
