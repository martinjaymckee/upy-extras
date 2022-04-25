import machine

import timestamp


class Event:
    Pressed = const(2)
    Released = const(4)
    Toggled = const(8)
    LongPressed = const(16)
    Clicked = const(32)
    RepeatClicked = const(64)

    __evt_type_str = {
        0: 'none',
        Pressed: 'Pressed',
        Released: 'Released',
        Toggled: 'Toggled',
        LongPressed: 'Long Pressed',
        Clicked: 'Clicked',
        RepeatClicked: 'Repeat Clicked'
    }    

    def __init__(self, state=None, evt_type=0):
        self.state = state
        self.evt_type = evt_type

    def __str__(self):
        type_list = []
        for key, value in Event.__evt_type_str.items():
            if not key == 0:
                if not self.evt_type & key == 0:
                    type_list.append(value)
        type_list_text = 'none'
        if len(type_list) == 1:
            type_list_text = type_list[0]
        else:
            type_list_text = '[{}]'.format(', '.join(type_list))
        return 'Event( state = {}, type = {} )'.format(self.state, type_list_text)
    
    @micropython.native
    def reset(self, state=None, evt_type=0):
        self.state = state
        self.evt_type = evt_type

    @property
    def active(self):
        return not (self.evt_type == 0)
    
    @property
    def pressed(self):
        return not (self.evt_type & Event.Pressed) == 0
    
    @property
    def released(self):
        return not (self.evt_type & Event.Released) == 0
    
    @property
    def toggled(self):
        return not (self.evt_type & Event.Toggled) == 0
    
    @property
    def long_pressed(self):
        return not (self.evt_type & Event.LongPressed) == 0
    
    @property
    def clicked(self):
        return not (self.evt_type & Event.Clicked) == 0
    
    @property
    def repeat_clicked(self):
        return not (self.evt_type & Event.RepeatClicked) == 0


class ButtonCore:
    samples = const(6)
    buffer_mask = const(0x3F)  # Calculated as (1<<ButtonCore.samples) - 1)
    
    def __init__(self, pin_num, pin_mode=machine.Pin.PULL_UP, inverted=None, f_sample=200):
        self.__pin = machine.Pin(pin_num, machine.Pin.IN, pin_mode)
        self.__inverted = inverted if inverted is not None else (pin_mode == machine.Pin.PULL_UP)
        self.state = False
        
        t = timestamp.now()
        self.__t_last = t
        
        self.__t_sample = int(1e6 / f_sample)
        self.__buffer = 0
        self.__event_mask = 0xFFFF
        self.event = Event()

    @property
    def latency_us(self):
        return self.__num_samples * self.__t_sample
    
    @property
    def f_max(self):
        return 1e6 / (2 * self.latency_us)
    
    @micropython.native    
    def core_reset(self, default_state=False):
        self.state = default_state
        t = timestamp.now()
        self.__t_last = t
        self.__buffer = 0
        
    def filter_events(self, events):
        self.__event_mask = 0xFFFF ^ events
       
    @micropython.native
    def until_event(self, evt_mask, func=None):
        while True:
            evt = self.update()
            if not (evt.evt_type & evt_flag) == 0:
                return
            else:
                if func is not None:
                    func()
                    
    @micropython.native       
    def wait_for_pressed(self, func=None):
        return self.until_event(Event.Pressed, func)

    @micropython.native       
    def wait_for_released(self, func=None):
        return self.until_event(Event.Released, func)
          
    @micropython.native
    def process_state(self, t, val, init_state):
        t_last = self.__t_last
        t_sample = self.__t_sample
        if timestamp.expired_at(t_last, t_sample, t):
            self.__t_last = timestamp.advance(t_last, t_sample)
            state = init_state
            buffer = self.__buffer
            buffer = ((buffer << 1) + int(val)) & ButtonCore.buffer_mask
            if (buffer == ButtonCore.buffer_mask) and (not state):
                state = True
            elif (buffer == 0) and state:
                state = False
            self.__buffer = buffer
            return state, state ^ init_state
        return init_state, False
    
    
class Button(ButtonCore):
    def __init__(self, pin_num, pin_mode=machine.Pin.PULL_UP, inverted=None, f_sample=200, t_long_press=None, t_repeat_click=None):
        ButtonCore.__init__(self, pin_num, pin_mode, inverted, f_sample)

        t = timestamp.now()
        self.__t_changed = t
        self.__t_last_click = t
        self.__t_long_press = int(0.55 * 1e6) if t_long_press is None else t_long_press
        self.__t_repeat_click = int(0.4 * 1e6) if t_repeat_click is None else t_repeat_click
        self.__long_pressed = False
    
    @micropython.native    
    def reset(self, default_state=None):
            
        self.core_reset()
        t = timestamp.now()
        self.__t_changed = t
        self.__t_last_click = t
        self.__long_pressed = False
        if default_state is None:
            self.__state = self.__inverted ^ self.__pin.value()
        else:
            self.__state = default_state

    @micropython.native
    def wait_for_clicked(self, func=None):
        return self.until_event(Event.Clicked, func)

    @micropython.native            
    def wait_for_repeat_clicked(self, func=None):
        return self.until_event(Event.RepeatClicked, func)

    @micropython.native
    def wait_for_long_pressed(self, func=None):
        return self.until_event(Event.LongPressed, func)
                        
    @micropython.native            
    def update(self):
        t = timestamp.now()
        event = self.event
        button_val = self.__inverted ^ self.__pin.value()
        init_state = self.state
        t_last = self.__t_last
        t_sample = self.__t_sample
        state = init_state
        event.evt_type = 0
    
        if init_state and not self.__long_pressed:
            do_long_pressed = timestamp.expired_at(self.__t_changed, self.__t_long_press, t)
            if do_long_pressed:
                event.evt_type |= Event.LongPressed
                self.__long_pressed = True
            event.evt_type &= self.__event_mask                

        if timestamp.expired_at(t_last, t_sample, t):
            self.__t_last = timestamp.advance(t_last, t_sample)
            state = init_state
            buffer = self.__buffer
            buffer = ((buffer << 1) + int(button_val)) & ButtonCore.buffer_mask
            if (buffer == ButtonCore.buffer_mask) and (not state):
                state = True
            elif (buffer == 0) and state:
                state = False
            self.__buffer = buffer
            
            if state ^ init_state:
                event.state = state            
                self.__t_changed = t
                if state:
                    event.evt_type = Event.Pressed
                else:
                    event.evt_type = Event.Released
                    if not self.__long_pressed:
                        repeat_click = not timestamp.expired_at(self.__t_last_click, self.__t_repeat_click, t)
                        if repeat_click:
                            event.evt_type |= Event.RepeatClicked
                        else:
                            event.evt_type |= Event.Clicked                    
                        self.__long_pressed = False
                        self.__t_last_click = t                
                self.state = state
                event.evt_type &= self.__event_mask
        return event


class Toggle(ButtonCore):
    def __init__(self, pin_num, pin_mode=machine.Pin.PULL_UP, inverted=None, f_sample=200, on_release=False):
        ButtonCore.__init__(self, pin_num, pin_mode, inverted, f_sample)
        self.__on_release = on_release
        self.__last_state = self.state
                    
    @micropython.native    
    def reset(self, default_state=False):
        self.core_reset(default_state)
        self.__last_state = default_state            

    @micropython.native            
    def wait_for_toggled(self, func=None):
        return self.until_event(Event.Toggled, func)
            
    @micropython.native            
    def update(self):
        event = self.event
        button_val = self.__inverted ^ self.__pin.value()
        t_last = self.__t_last
        t_sample = self.__t_sample
        init_state = self.__last_state

        event.evt_type = 0
        
        if timestamp.expired_at(t_last, t_sample, timestamp.now()):
            self.__t_last = timestamp.advance(t_last, t_sample)
            state = init_state
            buffer = self.__buffer
            buffer = ((buffer << 1) + int(button_val)) & ButtonCore.buffer_mask
            if (buffer == ButtonCore.buffer_mask) and (not state):
                state = True
            elif (buffer == 0) and state:
                state = False
            self.__buffer = buffer
            if state ^ init_state:
                self.__last_state = state            
                on_release = self.__on_release
                if state:
                    event.evt_type = Event.Pressed
                    if not on_release:
                        event.evt_type |= Event.Toggled
                        self.state = not self.state        
                else:
                    event.evt_type = Event.Released
                    if on_release:
                        event.evt_type |= Event.Toggled
                        self.state = not self.state        
                event.state = self.state
                event.evt_type &= self.__event_mask                
        return event


class Unbuffered(ButtonCore):
    def __init__(self, pin_num, pin_mode=machine.Pin.PULL_UP, inverted=None, f_sample=200):
        ButtonCore.__init__(self, pin_num, pin_mode, inverted, f_sample)
                    
    @micropython.native    
    def reset(self, default_state=False):
        self.core_reset(default_state)
            
    @micropython.native            
    def update(self):
        event = self.event
        state = bool(self.__inverted ^ self.__pin.value())
        if state ^ self.state:
            event.state = state        
            if state:
                event.evt_type = Event.Pressed
            else:
                event.evt_type = Event.Released
            event.evt_type &= self.__event_mask
            self.state = state
        else:
            event.evt_type = 0
        return event
    