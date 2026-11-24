"""Indexed SD animation player: one row buffer, no second framebuffer."""
import gc
import struct
import deflate
import time

class Player:
    def __init__(self, lcd, index, directory='/sd/picodex_animations'):
        if index < 0:
            raise ValueError('Invalid animation index')
        self.index = index
        self.file = open(directory+'/pack-%02d.bin' % (index//128), 'rb')
        try:
            magic, entries = struct.unpack('<4sH', self.file.read(6))
            slot = index % 128
            if magic != b'PAX1' or not 1 <= entries <= 128 or slot >= entries:
                raise ValueError('Invalid animation pack')
            self.file.seek(6+slot*8)
            self.start, size = struct.unpack('<II', self.file.read(8))
            self.file.seek(0, 2)
            if self.start < 6+entries*8 or size < 14 or self.start+size > self.file.tell():
                raise ValueError('Incomplete packed animation')
            self.end = self.start+size
            self.file.seek(self.start)
            magic, self.width, self.height, self.count = struct.unpack('<4sHHH', self.file.read(10))
            if magic != b'PKA3' or not (1 <= self.width <= 192 and 1 <= self.height <= 64 and 2 <= self.count <= 256):
                raise ValueError('Invalid Pokemon animation')
            self.lcd = lcd
            self.screen = memoryview(lcd.buffer)
            self.row = bytearray(self.width*2)
            self.x = (240-self.width)//2
            self.y = (216-self.height*3)//2
            self.frame = 0
            self.due = time.ticks_ms()
            self.first = True
        except Exception:
            self.file.close()
            raise

    def step(self, now):
        if time.ticks_diff(now, self.due) < 0:
            return False
        if self.frame == 0:
            self.file.seek(self.start+10)
        delay, size = struct.unpack('<HH', self.file.read(4))
        end = self.file.tell()+size
        if not size or end > self.end:
            raise ValueError('Invalid animation frame boundary')
        gc.collect()
        stream = deflate.DeflateIO(self.file, deflate.RAW, 9)
        try:
            if not 60 <= delay <= 2000:
                raise ValueError('Invalid frame duration')
            if self.first:
                self.lcd.fill_rect(0, 0, 240, 216, 0)
                self.first = False
            length = len(self.row)
            for y in range(self.height):
                if stream.readinto(self.row) != len(self.row):
                    raise OSError('Incomplete animation row')
                for dy in (0, 1, 2):
                    pos = ((self.y+y*3+dy)*240+self.x)*2
                    self.screen[pos:pos+length] = self.row
        finally:
            stream.close()  # close=False leaves the underlying pack file open.
        del stream
        self.file.seek(end)
        self.lcd.show()
        self.frame = (self.frame+1) % self.count
        self.due = time.ticks_add(now, delay)
        return True

    def close(self):
        self.file.close()
