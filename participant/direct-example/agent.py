class Agent:
    def reset(self):
        pass

    def act(self, observation):
        # Direct rim-rod benchmark only: 22 observations, three length-speed commands.
        # Positive extends, negative retracts, zero holds commanded length.
        return [0.0, 0.0, 0.0]
