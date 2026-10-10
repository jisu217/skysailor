"""Constant-velocity Kalman filter on x=[p(3), v(3)] in ENU.

Inputs are positions: triangulated camera fixes (ops.localization) or Remote ID reports.
"""
import numpy as np

H = np.hstack([np.eye(3), np.zeros((3, 3))])


class KalmanCV:
    def __init__(self, x0, P0, q: float = 1.0):
        self.x, self.P, self.q = np.asarray(x0, float), np.asarray(P0, float), q

    def predict(self, dt: float):
        if dt <= 0:
            return
        I = np.eye(3)
        F = np.block([[I, dt*I], [0*I, I]])
        Q = self.q*np.block([[dt**3/3*I, dt**2/2*I], [dt**2/2*I, dt*I]])
        self.x = F@self.x
        self.P = F@self.P@F.T+Q

    def mahalanobis2(self, z, R) -> float:
        y = np.asarray(z, float)-H@self.x
        S = H@self.P@H.T+np.asarray(R, float)
        return float(y@np.linalg.solve(S, y))

    def update(self, z, R) -> float:
        z, R = np.asarray(z, float), np.asarray(R, float)
        y = z-H@self.x
        S = H@self.P@H.T+R
        K = self.P@H.T@np.linalg.inv(S)
        self.x = self.x+K@y
        IKH = np.eye(6)-K@H
        self.P = IKH@self.P@IKH.T+K@R@K.T
        return float(y@np.linalg.solve(S, y))
