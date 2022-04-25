import machine
import time

import button
import perf
import timestamp

    
if __name__ == '__main__':
    test_type = 'perf_all'
    correct_samples = 15
    perf_bins = 50
    
    board_led = machine.Pin(25, machine.Pin.OUT)
    state_led = machine.Pin(16, machine.Pin.OUT)
    perf_btn = button.Button(18) 
    perf_sampler = perf.HistogramSampler(bins=perf_bins, t_sample_us=int(1.5e6))

    def perfCorrectTiming():
        t_correct = 0
        correct_sampler = perf.HistogramSampler(bins=perf_bins, t_sample_us=1000000)
        print('Running perf correction measurement:')
        for idx in range(correct_samples):
            print('\tSample {}'.format(idx + 1))
            updated = False
            while not updated:
                correct_sampler.begin()
                updated = correct_sampler.end()
                if updated:
                    t_correct += correct_sampler.data.mean
        t_correct = t_correct / correct_samples
        del correct_sampler
        return t_correct
    
    t_perf_offset = 0
    
    def displayPerfInfo(btn):
        print('\n{}.update() Performance:'.format(btn.__class__.__name__))
        data = perf_sampler.data
        data.print_histogram()
        print('\tmean = {} us'.format(data.mean - t_perf_offset))
        
    def testRunner(msg, btn, evt_processor, timeout_s=None):
        print(msg)
        pulsing = False
        t_start = timestamp.now()
        t_pulse = 50000
        t_update = None
        timeout_us = None if timeout_s is None else 1e6*timeout_s
        perf_sampler.reset()
        t_begin = timestamp.now()
        while True:
            perf_sampler.begin()
            evt = btn.update()
            perf_updated = perf_sampler.end()
            evt_processor(evt)
            state_led.value(btn.state)            
            if perf_updated:
                t_start = timestamp.now()
                pulsing = True
                board_led.value(True)
                new_t_update = perf_sampler.data.mean - t_perf_offset
                if (t_update is None) or (t_update > new_t_update):
                    t_update = new_t_update
            if pulsing and timestamp.expired(t_start, t_pulse):
                board_led.value(False)
                pulsing = False
            evt = perf_btn.update()
            force_exit = (timeout_us is not None) and (timestamp.expired(t_begin, int(timeout_us)))
            if evt.clicked:
                displayPerfInfo(btn)
            elif evt.long_pressed or force_exit:
                break
        print('\nExiting!')
        if t_update is not None:
            print('\tBest mean(t_update) = {} us'.format(t_update))
        return t_update
        
    def simpleEventProcessor(evt):
        if evt.pressed or evt.released:
            print(evt)
                        
    def toggleEventProcessor(evt):
        if evt.toggled or evt.pressed or evt.released:
            print(evt)
    
    def perfProcessor(evt):
        return
    
    if test_type == 'simple':
        testRunner('Running Simple Pushbutton Test', button.Button(19), simpleEventProcessor)       
    elif test_type == 'toggle':
        testRunner('Running Toggle Test', button.Toggle(19), toggleEventProcessor) 
    elif test_type == 'unbuffered':
        testRunner('Running Unbufered Switch Test', button.Unbuffered(19), simpleEventProcessor) 

    elif test_type == 'perf_all':
        results = {}
        timeout_s = 120
        t_perf_offset = perfCorrectTiming()
        print('t_perf_offset = {} us'.format(t_perf_offset))        
        results['simple'] = testRunner('Running Simple Pushbutton Test', button.Button(19), perfProcessor, timeout_s=timeout_s)        
        results['toggle'] = testRunner('Running Toggle Test', button.Toggle(19), perfProcessor, timeout_s=timeout_s)
        results['unbuffered'] = testRunner('Running Unbuffered Switch Test', button.Unbuffered(19), perfProcessor, timeout_s=timeout_s)
        
        for type_name, result in results.items():
            print('{} -> {}'.format(type_name, result))
        