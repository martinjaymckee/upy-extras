import time

@micropython.native
def __get_ticks_mask():
    ticks_max = time.ticks_add(0, -1)  # Note: This is taken from the documentation
    bits = 0
    while ticks_max > (2**bits - 1):
        bits += 1
    return (2**bits - 1)
__ticks_mask = __get_ticks_mask()


@micropython.viper
def diff(t1: uint, t0: uint) -> uint:
    return (t1 - t0) if (t1 > t0) else (uint(__ticks_mask) - t1 + t0)

@micropython.viper
def advance(t: uint, delta: uint) -> uint:
    return uint(__ticks_mask) & (t + delta)


@micropython.viper
def now() -> uint:
    return uint(time.ticks_us()) & uint(__ticks_mask)


@micropython.viper
def expired_at(t_base: uint, us: uint, t: uint) -> bool:
    return ((t - t_base) if (t > t_base) else (uint(__ticks_mask) - t + t_base)) >= us


@micropython.viper
def expired(t_base: uint, us: uint) -> bool:
    return bool(expired_at(t_base, us, now()))


@micropython.native
def expired_and_advance(t_base, us, t=None):
    t = now() if t is None else t
    result = expired_at(t_base, us, t)
    return result, advance(t_base, us) if result else t_base


if __name__ == '__main__':
    import machine
    
    led = machine.Pin(25, machine.Pin.OUT)
    
    def toggle():
        led.value( not led.value() )

    t_base = now()
    t_period = 1000 * 500
    
    while True:
        do_toggle, t_base = expired_and_advance(t_base, t_period)
        if do_toggle:
            toggle()
        
