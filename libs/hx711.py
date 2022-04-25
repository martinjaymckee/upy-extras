import machine
import rp2
import time

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, in_shiftdir=0)
def __hx711_pio_read(): #CHA Gain = 128
    wrap_target()
    wait(0, pin, 0)
    set(x, 23)
    label('read')
    set(pins, 1)[3]
    in_(pins, 1)
    set(pins, 0)
    jmp(x_dec, 'read')
    set(pins, 1)[3]
    set(pins, 0)[3]
    push(noblock)
    irq(0)  
    wrap()


class HX711:
    def __irq_handler(self, pio):
        self.__sm.exec('irq(clear, 0)')        
        t = time.ticks_us()
        data = self.__sm.get()
        if data >= 0x800000:
            data = data - 0xFFFFFF
        dt = 0 if self.__t_last is None else t - self.__t_last
        self.__t_last = t
        #self.__fifo.append( (dt, data) )
        self.__dt = dt
        self.__data = data
        
    def __init__(self, clk, dt, pio_idx=0):
        self.__sm = rp2.StateMachine(pio_idx, __hx711_pio_read, freq=1000000, set_base=machine.Pin(clk), in_base=machine.Pin(dt))
        self.__sm.active(1)
        #rp2.PIO(pio_idx).irq(self.__irq_handler)
#         self.__fifo = []
        self.__dt = None
        self.__data = None
        self.__t_last = None
        
    def __len__(self):
        return 1 if self.__data is not None else 0

    def valid(self):
        return self.__data is not None
    
    def available(self):
        return self.__sm.rx_fifo()
    
    def get(self):
        data = self.__sm.get()
        if data >= 0x800000:
            data = data - 0xFFFFFF
        return data
    
#         print('irq flags = {}'.format(self.__sm.irq().flags()))
#         if len(self) == 1:
#             ret = (self.__dt, self.__data)
#             self.__data = None
#             return ret
#         return None, None
#         if len(self) > 0:
#             pre = len(self.__fifo)
#             t, data = self.__fifo.pop(0)
#             post = len(self.__fifo)
#             print(pre, post)
#             return t, data
#         return None, None