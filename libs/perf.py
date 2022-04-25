import math
import utime

import timestamp

@micropython.native
class HistogramSampler:
    class HistogramData:
        def __init__(self, t_min_us, t_max_us, t_start, t_sample_us, num_bins):
            self.__t_min_us = t_min_us
            self.__t_max_us = t_max_us
            self.__t_start = t_start
            self.__t_sample_us = t_sample_us
            self.__num_bins = num_bins
            self.__bins = [0] * self.__num_bins            
            self.__done = False
            self.__t_total_us = 0
            self.__samples = 0
            self.__t_step = (t_max_us - t_min_us) / num_bins
            self.__t_minimum = None
            self.__t_maximum = None
            
        def reset(self, t_min_us, t_max_us, t_start):
            self.__t_min_us = t_min_us
            self.__t_max_us = t_max_us
            self.__t_start = t_start            
            self.__done = False
            self.__t_total_us = 0
            self.__samples = 0
            self.__t_step = (t_max_us - t_min_us) / self.__num_bins
            self.__t_minimum = None
            self.__t_maximum = None
            for idx in range(self.__num_bins):
                self.__bins[idx] = 0

        @property
        def num_bins(self):
            return self.__num_bins
        
        @property
        def dt_min(self):
            return self.__t_min_us
        
        @property
        def dt_max(self):
            return self.__t_max_us
        
        @property
        def t_start(self):
            return self.__t_start
        
        @property
        def histogram(self):
            hist = []
            t_min = self.__t_min_us
            for idx, count in enumerate(self.__bins):
                t_max = t_min + self.__t_step
                hist.append( ((t_min, t_max), count) )
                t_min = t_max
            return hist
        
        @property
        def percentage(self):
            return 100 * (self.__t_total_us / self.__t_sample_us)
        
        
        @property
        def minimum(self):
            return self.__t_minimum
        
        @property
        def maximum(self):
            return self.__t_maximum
        
        @property
        def mean(self):
            if self.__samples == 0: return None
            hist = self.histogram
            total = 0
            for (minimum, maximum), count in hist:
                total += (maximum + minimum) * count / 2
            return total / self.__samples
        
        @property
        def variance(self):
            mean = self.mean
            hist = self.histogram
            total = 0
            for (minimum, maximum), count in hist:
                mid = (maximum + minimum) / 2
                total += (mid - mean)**2 * count
            return total / self.__samples
    
        @property
        def sd(self):
            return math.sqrt(self.variance)
        
        @property
        def samples(self):
            return self.__samples
        
        @property
        def valid(self):
            return self.__done
    
        @micropython.native
        def add(self, t0, t1, use=False):
            dt = timestamp.diff(t1, t0)
            if use and not self.__done:
                self.__t_total_us += dt
                idx = self.__bin_idx(dt)
                self.__bins[idx] += 1
                self.__samples += 1
                if (self.__t_minimum is None) or (self.__t_minimum > dt):
                    self.__t_minimum = dt
                if (self.__t_maximum is None) or (self.__t_maximum < dt):
                    self.__t_maximum = dt                    
            self.__done = (t1 - self.__t_start) >= self.__t_sample_us
            return self.__done

        def print_histogram(self, width=80):
            counter = '#'
            fill = ' '
            hist = self.histogram
            max_count = 0
            field_width = int(math.ceil(math.log10(self.__t_max_us)))
            line_fmt = r'{{:{}d}} us - {{:{}d}} us: {{}}{{}}|'.format(field_width, field_width)
            scale_fmt = r'{{:{}d}} |'.format(width - 3)
            label_width = 12 + 2 * field_width
            for (_, _), count in hist:
                if count > max_count:
                    max_count = count
            hist_width = width - label_width - 1
            if max_count == 0:
                print('No samples taken')
            else:
                counter_weight = hist_width / max_count
                for (minimum, maximum), count in hist:
                    num_counters = int(math.ceil(counter_weight * count))
                    num_fill = hist_width - num_counters
                    print(line_fmt.format(int(minimum), int(maximum), counter * num_counters, fill * num_fill))
                print(scale_fmt.format(int(max_count)))
            return
        
        def __bin_idx(self, dt):
            return int(max(0, min((dt - self.__t_min_us) / self.__t_step, self.__num_bins - 1)))

    def __init__(self, t_min_us=None, t_max_us=None, t_sample_us=None, bins=None, auto_rescale=True): 
        self.__t_min_us = 0 if t_min_us is None else t_min_us
        self.__t_max_us = 1500 if t_max_us is None else t_max_us
        self.__t_sample_us = max(1e6, 10 * self.__t_max_us) if t_sample_us is None else t_sample_us
        self.__num_bins = 10 if bins is None else bins
        self.__auto_rescale = auto_rescale
        self.__data_buffer = [
            self.HistogramData(self.__t_min_us, self.__t_max_us, 0, self.__t_sample_us, self.__num_bins),
            self.HistogramData(self.__t_min_us, self.__t_max_us, 0, self.__t_sample_us, self.__num_bins)
        ]
        self.__active_idx = 0
        self.reset()
    
    @property
    def data(self):
        return self.__data_buffer[1-self.__active_idx]
    
    def reset(self):
        t_start = timestamp.now()
        self.__sampling = False
        self.__active_idx = 0        
        for data in self.__data_buffer:
            data.reset(self.__t_min_us, self.__t_max_us, t_start)
        
    @micropython.native
    def begin(self):
        self.__sampling = True
        self.__t0 = timestamp.now()        

    @micropython.native
    def end(self, keep=True):
        t1 = timestamp.now()
        use = keep and self.__sampling
        active_data = self.__data_buffer[self.__active_idx]
        done = active_data.add(self.__t0, t1, use=use)
        self.__sampling = False
        if done:
            t_min_us = active_data.minimum if self.__auto_rescale else self.__t_min_us
            t_max_us = active_data.maximum if self.__auto_rescale else self.__t_max_us            
            self.__active_idx = 0 if self.__active_idx == 1 else 1
            self.__data_buffer[self.__active_idx].reset(t_min_us, t_max_us, t1)
        return done
    
    @micropython.native    
    def end_callback(self, callback, keep=True):
        t1 = timestamp.now()
        use = keep and self.__sampling
        active_data = self.__data_buffer[self.__active_idx]
        done = active_data.add(self.__t0, t1, use=(keep and self.__sampling))
        self.__sampling = False
        if use and (callback is not None):
            callback(self.__t0, t1)
        if done:
            t_min_us = active_data.minimum if self.__auto_rescale else self.__t_min_us
            t_max_us = active_data.maximum if self.__auto_rescale else self.__t_max_us            
            self.__active_idx = 0 if self.__active_idx == 1 else 1
            self.__data_buffer[self.__active_idx].reset(t_min_us, t_max_us, t1)
        return done
    



class perf:
    __history = []
    
    def __init__(self, func, name=None, stats=None):
        self.__func = func
        self.__stats = HistogramSampler() if stats is None else stats
        # TODO: STORE A LINK TO THIS IN THE PERF HISTORY LIST AND MAKE IT ACCESSIBLE FROM THE PERF CLASS
    def __call__(self, *args, **kwargs):
        self.__stats.begin()
        result = self.__func(*args, **kwargs)
        self.__stats.end()
        return result


if __name__ == '__main__':
    import random
    
    t_min = 500
    t_max = 5000
    
    def rand_sleep_us():
        us = random.randint(t_min, t_max)
        utime.sleep_us(us)
        return us
    
    stats = HistogramSampler(t_min_us=t_min, t_max_us=1.05*t_max, t_sample_us=10e6)
    data = None
    
    while True:
        stats.begin()
        us = rand_sleep_us()
        updated = stats.end()
        
        data = stats.data
        if updated: # and (data is not None) and (data.valid):
            print('Target:')
            print('\tpercentage = 100%')
            print('\tminimum = {}us'.format(t_min))
            mean = (t_max + t_min) / 2
            sd = math.sqrt((t_max - t_min)**2 / 12)
            print('\tmean = {} us (+/- {} us)'.format(mean, sd))
            print('\tmaximum = {} us'.format(t_max))
            print('\tsamples = {}'.format(int(1e6 / mean)))
            print('')
            print('Measured:')
            print('\tpercentage = {}%'.format(data.percentage))
            print('\tminimum = {}us'.format(data.minimum))
            print('\tmean = {} us (+/- {} us)'.format(data.mean, data.sd))    
            print('\tmaximum = {}us'.format(data.maximum))
            print('\tsamples = {}'.format(data.samples))
            data.print_histogram() 