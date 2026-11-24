"""Exercise repeated entry changes with real SD/LCD and simulated taps."""
import gc,machine
from machine import Pin
from lcd import LCD_1inch54
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
            if Bus.n>40:raise KeyboardInterrupt
            down=Bus.n in (3,6,9,12,15,18,21,24,27,30,33)
            return bytes([int(down),0,220,0,120])
        if addr==0x6b and reg==0x35:return bytes(6)
        return self.bus.readfrom_mem(addr,reg,n)
frames=0

def probe(event):
    global frames
    if event=='frame':frames+=1
frame_app.I2C=Bus
try:frame_app.start(lcd,power,Pin(24,Pin.IN,Pin.PULL_UP),_probe=probe)
except KeyboardInterrupt:
    if frames<10:raise ValueError('Not enough animated entry frames: '+str(frames))
    print('PASS repeated browsing; frames',frames)
