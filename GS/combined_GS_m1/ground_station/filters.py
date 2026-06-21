import collections
import math

class ExponentialMovingAverage:
    """
    Applies an Exponential Moving Average filter to smooth noisy sensor data.
    alpha is the smoothing factor between 0 and 1.
    Higher alpha = faster response to change, less smoothing.
    Lower alpha = slower response, more smoothing.
    """
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.current_value = None

    def update(self, new_value):
        if self.current_value is None:
            self.current_value = new_value
        else:
            self.current_value = (self.alpha * new_value) + ((1.0 - self.alpha) * self.current_value)
        return self.current_value


class OutlierRejectionFilter:
    """
    Rejects sudden spikes in data that exceed a maximum allowed delta from the previous reading.
    Useful for filtering GPS multipath jumps or pressure sensor glitches.
    """
    def __init__(self, max_delta=50.0):
        self.max_delta = max_delta
        self.last_valid = None

    def update(self, new_value):
        if self.last_valid is None:
            self.last_valid = new_value
            return new_value
            
        if abs(new_value - self.last_valid) > self.max_delta:
            # Reject outlier, return the last known good value
            return self.last_valid
            
        self.last_valid = new_value
        return new_value


class MovingAverageFilter:
    """
    Standard simple moving average over N samples.
    """
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.history = collections.deque(maxlen=window_size)

    def update(self, new_value):
        self.history.append(new_value)
        return sum(self.history) / len(self.history)
