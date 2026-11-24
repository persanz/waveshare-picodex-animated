"""Lean real-board test. Compile/upload, then run(order_index)."""
import gc,time,machine,binascii
from machine import Pin
from lcd import LCD_1inch54

def run(index):
    gc.threshold(1024)
    power=Pin(28,Pin.OUT,value=1)
    gc.collect();lcd=LCD_1inch54()
    import frame_app
    real_i2c=machine.I2C
    class Bus:
        n=0
        def __init__(self,*a,**kw):self.bus=real_i2c(*a,**kw)
        def writeto_mem(self,*a):return self.bus.writeto_mem(*a)
        def readfrom_mem(self,addr,reg,n):
            if addr==0x15 and reg==2:
                Bus.n+=1
                if Bus.n>100:raise KeyboardInterrupt
                down=31<=Bus.n<=53 or 61<=Bus.n<=63
                return bytes([int(down),0,120,0,120])
            if addr==0x6b and reg==0x35:return bytes(6)
            return self.bus.readfrom_mem(addr,reg,n)
    state=[None,False,0,0,0,0,999999]
    def probe(event):
        if event=='pause':state[0]=binascii.crc32(lcd.buffer)
        elif event=='return':state[1]=binascii.crc32(lcd.buffer)==state[0]
        elif event=='frame':
            if Bus.n<31:
                now=time.ticks_ms()
                if not state[2]:state[4]=now
                state[2]+=1;state[5]=now;state[6]=min(state[6],gc.mem_free())
            if Bus.n>=64:state[3]+=1
    frame_app.I2C=Bus
    try:frame_app.start(lcd,power,Pin(24,Pin.IN,Pin.PULL_UP),initial_index=index,_probe=probe)
    except KeyboardInterrupt:
        if state[2]<2 or not state[1] or state[3]<5:raise ValueError('Playback/description/resume failed: '+str(state))
        print('PASS catalog entry',index,'frames',state[2],'after',state[3],'fps',round((state[2]-1)*1000/max(1,time.ticks_diff(state[5],state[4])),2),'min_free_heap',state[6])
