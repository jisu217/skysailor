class Agent:
    def reset(self):
        pass

    def act(self, observation):
        # Hanging benchmark only: 28 observations, three length-speed commands.
        # Positive extends, negative retracts, zero holds commanded length.
        return [0.0, 0.0, 0.0]
