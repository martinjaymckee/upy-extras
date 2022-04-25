import machine
import rp2
import time

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, in_shiftdir=0, fifo_join=rp2.PIO.JOIN_RX)
def __hx711_pio_read(): #CHA Gain = 128
    wrap_target()
    label('init')
    mov(y, invert(null))
    label('delay')
    jmp(pin, 'dec')
    jmp('init_read')
    label('dec')
    jmp(y_dec, 'delay')
    jmp('ovf')
    label('init_read')
    set(x, 23)[3]
    label('read')
    set(pins, 1)[3]
    in_(pins, 1)[2]
    set(pins, 0)[4]
    jmp(x_dec, 'read')
    set(pins, 1)[5]
    set(pins, 0)[2]
    push(noblock)
    mov(isr, y)
    push(noblock)
    wrap()
    label('ovf')
    mov(isr, invert(null))
    push(noblock)
    push(noblock)
    jmp('init')


class HX711:
    f_clk = const(20000000)
    dt_count_ratio = const(2)
    dt_counts_read = const(256)
    dt_counts_ovf = const(5)
    
    def __init__(self, clk, dt, pio_idx=0):
        self.__sm = rp2.StateMachine(pio_idx, __hx711_pio_read, freq=HX711.f_clk, set_base=machine.Pin(clk), in_base=machine.Pin(dt), jmp_pin=machine.Pin(dt))
        self.__sm.active(1)
        self.__dt_res = HX711.dt_count_ratio / HX711.f_clk
        print('dt_res = {} us'.format(1e6 * self.__dt_res))
        
    def __len__(self):
        return 1 if self.__data is not None else 0

    @micropython.native
    def valid(self):
        return self.__data is not None
    
    @micropython.native
    def available(self):
        return self.__sm.rx_fifo()
    
    @micropython.native
    def get(self):
        data = self.__sm.get()
        dt_data = self.__sm.get()
        valid_data = not (data == 0xFFFFFFFF)
        if valid_data:
            dt = (0xFFFFFFFF - dt_data + HX711.dt_counts_read) * self.__dt_res
            if data >= 0x800000:
                data = data - 0xFFFFFF
            return data, dt
        return None, (0xFFFFFFFF + HX711.dt_counts_ovf) * self.__dt_res
