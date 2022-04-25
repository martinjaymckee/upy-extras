import math

class ExponentialStatistics:
    def __init__(self, fs=100, tau=1):
        assert tau > 0, 'Error: Negative time constant (tau) is invalid'
        assert fs > 0, 'Error: Negative sample rate (fs) is invalid'
        self.__x = None
        self.__s2 = None
        self.__e = self.__calc_weight(fs, tau)
        self.__fs = fs
        self.__tau = tau
        self.__samples = 0

    def reset(self):
        self.__x = None
        self.__s2 = None
        self.__samples = 0
        
    @property
    def x(self):
        return self.__x
    
    @property
    def s2(self):
        return self.__s2
    
    @property
    def s(self):
        return math.sqrt(self.s2)

    @property
    def SE(self):
        n = math.log(0.5) / math.log(self.e)
        return self.s / math.sqrt(n)
    
    @property
    def e(self):
        return self.__e
    
    @property
    def samples(self):
        return self.__samples
    
    @property
    def valid(self):
        return self.__x is not None

    @property
    def fs(self):
        return self.__fs
    
    @fs.setter
    def fs(self, val):
        assert val > 0, 'Error: Negative sample rate (fs) is invalid'
        self.__e = self.__calc_weight(val, self.tau)
        self.__fs = val
        return val

    @property
    def tau(self):
        return self.__tau
    
    @tau.setter
    def tau(self, val):
        assert val > 0, 'Error: Negative time constant (tau) is invalid'
        self.__e = self.__calc_weight(self.fs, val)
        self.__tau = val
        return val

    @micropython.native
    def update(self, x_new):
        e = self.__e
        x = self.__x
        s2 = self.__s2
        if x is None:
            x = x_new
            s2 = 0
        else:
            diff = (x - x_new)
            x = (e * diff) + x_new
            s2_new = diff * diff
            s2 = (e * (s2 - s2_new)) + s2_new
        self.__x = x
        self.__s2 = s2
        self.__samples += 1
        return x
        
    @micropython.native        
    def __calc_weight(self, fs, tau):
        assert tau > (5 * (1/fs)), 'Error: Time constant (tau) too short for sample rate'    
        return math.exp(-1/(fs * tau))


class RunningStatistics:
    def __init__(self):
        self.__x = None
        self.__s2_sum = None
        self.__samples = 0

    def reset(self):
        self.__x = None
        self.__s2_sum = None
        self.__samples = 0
        
    @property
    def x(self):
        return self.__x
    
    @property
    def s2(self):
        samples = self.__samples
        if samples <= 2:
            return None if self.__s2_sum is None else 0
        return self.__s2_sum / (self.__samples - 1)
    
    @property
    def s(self):
        return math.sqrt(self.s2)

    @property
    def SE(self):
        return self.s / math.sqrt(self.__samples)

    @property
    def samples(self):
        return self.__samples
    
    @property
    def valid(self):
        return self.__x is not None

    @micropython.native
    def update(self, x_new):
        x = self.__x
        s2_sum = self.__s2_sum
        samples = self.__samples + 1
        if x is None:
            x = x_new
            s2_sum = 0
        else:
            diff = (x_new - x)
            x += (diff / samples)
            s2_sum += (diff * (x_new - x))
        self.__x = x
        self.__s2_sum = s2_sum
        self.__samples = samples
        return x
