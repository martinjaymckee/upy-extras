import time

import hx711

clk_pin = 22
dat_pin = 21
samples = 100

if __name__ == '__main__':
    time.sleep(0.1)
    
    adc = hx711.HX711(clk_pin, dat_pin)
    
    count = 0
    while count < samples:
        if adc.available():
            data, dt = adc.get()
            print('count = {}, data = {}, dt = {}'.format(count, data, dt))
            count += 1
    