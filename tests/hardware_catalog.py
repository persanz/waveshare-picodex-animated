"""Compile/upload, then call run(order_index) via mpremote on a real board."""
import gc,time,machine,hashlib
from machine import Pin
from lcd import LCD_1inch54

def run(index):
    global lcd,held_hash,frames,first,last,free,restored,saw_description
    gc.threshold(1024)
    power=Pin(28,Pin.OUT,value=1)
    gc.collect();lcd=LCD_1inch54()
    import frame_app
    held_hash=None;frames=0;first=last=0;free=999999
    restored=saw_description=False
    real_i2c=machine.I2C
    class Bus:
        n=0
        def __init__(self,*a,**kw):self.bus=real_i2c(*a,**kw)
        def writeto_mem(self,*a):return self.bus.writeto_mem(*a)
        def readfrom_mem(self,addr,reg,n):
            global held_hash
            if addr==0x15 and reg==2:
                Bus.n+=1
                if Bus.n==41:held_hash=hashlib.sha256(lcd.buffer).digest()
                if Bus.n>95:raise KeyboardInterrupt
                down=41<=Bus.n<=63 or 71<=Bus.n<=73
                return bytes([int(down),0,120,0,120])
            if addr==0x6b and reg==0x35:return bytes(6)
            return self.bus.readfrom_mem(addr,reg,n)
    real_show=lcd.show
    def capture():
        global frames,first,last,free,restored,saw_description
        now=time.ticks_ms()
        if 1<=Bus.n<=40:
            frames+=1
            if not first:first=now
            last=now;free=min(free,gc.mem_free())
        if 55<=Bus.n<=70:saw_description=True
        if Bus.n==71:restored=restored or hashlib.sha256(lcd.buffer).digest()==held_hash
        real_show()
    lcd.show=capture;frame_app.I2C=Bus
    try:frame_app.start(lcd,power,Pin(24,Pin.IN,Pin.PULL_UP),initial_index=index)
    except KeyboardInterrupt:
        assert frames>=2,frames
        assert saw_description
        assert restored,'Animation frame not restored'
        print('PASS catalog entry',index,'frames',frames,'fps',round((frames-1)*1000/max(1,time.ticks_diff(last,first)),2),'min_free_heap',free)
