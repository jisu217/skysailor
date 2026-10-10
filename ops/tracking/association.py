"""Measurement-to-track association: Mahalanobis gate, then greedy nearest assignment.

Greedy is enough for demo target counts; swap in Hungarian only if tracks swap IDs.
"""
CHI2_3DOF = {0.95: 7.815, 0.99: 11.345, 0.999: 16.266}


def associate(tracks, detections, gate_p: float = 0.999):
    """tracks: objects with .kf (KalmanCV) → (pairs [(track, det)], unassigned_tracks, unassigned_dets)."""
    gate = CHI2_3DOF[gate_p]
    cand = []
    for i, tr in enumerate(tracks):
        for j, d in enumerate(detections):
            d2 = tr.kf.mahalanobis2(d.measurement.z, d.measurement.R)
            if d2 <= gate:
                cand.append((d2, i, j))
    used_t, used_d, pairs = set(), set(), []
    for _, i, j in sorted(cand):
        if i in used_t or j in used_d:
            continue
        used_t.add(i); used_d.add(j)
        pairs.append((tracks[i], detections[j]))
    return (pairs, [t for i, t in enumerate(tracks) if i not in used_t],
            [d for j, d in enumerate(detections) if j not in used_d])
