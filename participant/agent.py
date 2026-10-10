"""Participant contract: Agent.reset(seed), Agent.act(observation) -> float[2]."""
import numpy as np

class Agent:
    def reset(self, seed):
        pass

    def act(self, observation):
        # Neutral motor commands; not active position holding.
        return np.zeros(2, dtype=np.float32)
