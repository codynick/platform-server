"""Run generated demo loops once with synthetic sensors, no hardware/database."""
from pathlib import Path
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def check(project, temperature=25, distance=50, direction='neutral'):
    cards, leds, displays = {}, {}, []
    dashboard = types.ModuleType('Dashboard')
    class Card:
        def __init__(self, kind, title, **settings):
            self.type = kind
            self.__dict__.update(settings)
            cards[title] = self
        def set(self, value): self.value = value
        def save(self): pass
        def delete(self): pass
    dashboard.Card = Card
    dashboard.clear = cards.clear
    cody = types.ModuleType('CodyNick')
    class Simulator:
        def __init__(self, required_gadgets): self.required = required_gadgets
        def close(self): pass
    class Temperature:
        @staticmethod
        def read(cody): return temperature
    class Distance:
        @staticmethod
        def read(cody, device): return distance
    class Seven:
        @staticmethod
        def display(cody, device, value): displays.append(value)
    class RGB:
        @staticmethod
        def set(cody, index, colour): leds[index] = colour
        @staticmethod
        def clear(cody): leds.clear()
    class Joystick:
        @staticmethod
        def click(cody, device): return direction == 'click'
        @staticmethod
        def position(cody, device, pos): return direction == pos
    for name, value in [('Simulator', Simulator), ('Temperature_Sensor', Temperature), ('Ultrasonic_Sensor', Distance), ('Seven_Segment', Seven), ('RGB_Matrix', RGB), ('Joystick', Joystick)]:
        setattr(cody, name, value)
    def stop(_): raise KeyboardInterrupt
    with patch.dict(sys.modules, CodyNick=cody, Dashboard=dashboard), patch('time.sleep', stop):
        exec(compile((ROOT / 'test-output' / (project + '.py')).read_text(encoding='utf-8'), project, 'exec'), {})
    return cards, leds, displays


cards, _, display = check('01_temperature_monitor', temperature=21.5)
assert display == [21.5] and cards['Temperature (C)'].value == 21.5
assert cards['Temperature History'].value == [{'x': 1, 'y': 21.5}]
for temperature, colour in [(19.9, '#0000FF'), (20, '#00FF00'), (30, '#00FF00'), (30.1, '#FF0000')]:
    cards, leds, display = check('02_temperature_traffic_light', temperature=temperature)
    assert leds[6] == colour and display == [temperature]
for distance, colour in [(19.9, '#FF0000'), (20, '#00FF00'), (100, '#00FF00')]:
    cards, leds, _ = check('03_parking_assistant', distance=distance)
    assert leds[6] == colour and cards['Distance (cm)'].value == distance
for direction, index, colour in [('up', 13, '#0000FF'), ('down', 1, '#FFFF00'), ('left', 8, '#00FFFF'), ('right', 4, '#FF0000'), ('click', 6, '#FFFFFF'), ('neutral', None, None)]:
    cards, leds, _ = check('04_joystick_status', direction=direction)
    assert leds == ({index: colour} if index is not None else {})
    assert cards['Joystick Direction'].value == ('Pressed' if direction == 'click' else direction.title())
print('Four demos passed: live seven-segment/gauge/history, all temperature boundaries, parking threshold and all joystick directions/click/neutral.')
