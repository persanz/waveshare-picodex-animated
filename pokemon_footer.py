"""Load the footer renderer only when changing entries, not during playback."""
import struct
WHITE, ORANGE, BLACK = 0xffff, 0x20fd, 0

def draw(lcd, number, name):
    # Draw a footer band with the Pokémon number (white) before the name (orange).
    lcd.fill_rect(0, 216, 240, 24, BLACK)
    # Form IDs above 10000 are PokeAPI identifiers, not Pokédex numbers.
    if number >= 10000:
        try:
            with open('/pokemon_dex.bin', 'rb') as dex:
                dex.seek((number - 10000) * 2)
                entry = dex.read(2)
            number = struct.unpack('<H', entry)[0] if len(entry) == 2 else 0
        except OSError:
            number = 0
    num_label = str(number) if number else '?'
    max_chars = 30  # 240px / 8px font
    if name:
        total = len(num_label) + 1 + len(name)
        if total <= max_chars:
            # number before name on one centred line, different colours
            start_x = (240 - total*8) // 2
            lcd.text(num_label, start_x, 224, WHITE)
            lcd.text(name, start_x + len(num_label)*8 + 8, 224, ORANGE)
        else:
            # long name: number on its own line, name centred below
            words = name.split(' ')
            line1 = ''
            for w in words:
                if len((line1 + ' ' + w).strip()) <= max_chars:
                    line1 = (line1 + ' ' + w).strip()
                else:
                    break
            rest = name[len(line1):].strip()
            line2 = rest if len(rest) <= max_chars else rest[:max_chars-1] + '…'
            lcd.text(num_label, (240 - len(num_label)*8)//2, 218, WHITE)
            lcd.text(line1, (240 - len(line1)*8)//2, 224, ORANGE)
            if line2:
                lcd.text(line2, (240 - len(line2)*8)//2, 232, ORANGE)
    else:
        lcd.text(num_label, (240 - len(num_label)*8)//2, 224, WHITE)
    lcd.show()
    return number
