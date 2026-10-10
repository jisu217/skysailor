"""Any control algorithm is allowed. Only observations enter, actions leave."""
import numpy as np

class Agent:
    def reset(self):
        # Called once per flight, in a fresh process. Load weights here if needed.
        self.steps = 0

    def act(self, observation):
        self.steps += 1
        # Replace with PID, MPC, a neural network, or a controller with memory.
        # [rail angular-speed command, carriage linear-speed command], each [-1,1].
        return np.zeros(2, dtype=np.float32)
