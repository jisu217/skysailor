"""Object detector on ground-received frames (drone / balloon / bird).

Runs on the ground station, not on the dome. A small pretrained detector fine-tuned on
public drone / balloon / bird images is enough to start.
"""


class Detector:
    def __init__(self, weights: str | None = None, min_confidence: float = 0.4):
        self.weights, self.min_confidence = weights, min_confidence

    def detect(self, frame, t: float, node_id: str):
        """TODO: → list[CameraDetection]."""
        raise NotImplementedError
