"""Generate the four small, editable classroom Blockly designs."""
import json
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / 'upstream/components/examples/blockly'


def block(kind, fields=None, inputs=None, **extra):
    value = {'type': kind, **extra}
    if fields:
        value['fields'] = fields
    if inputs:
        value['inputs'] = {key: {'block': item} for key, item in inputs.items()}
    return value


def chain(*items):
    for first, second in zip(items, items[1:]):
        first['next'] = {'block': second}
    return items[0]


def number(value):
    return block('math_number', {'NUM': value})


def variable(name):
    return block('variables_get', {'VAR': {'id': name}})


def assign(name, value):
    return block('variables_set', {'VAR': {'id': name}}, {'VALUE': value})


def create(kind, name, title):
    return block('dash_create_' + kind, {'NAME': name, 'TITLE': title})


def update(name, value, kind='gauge'):
    return block('dash_' + kind + '_set', {'NAME': name}, {'VALUE': value})


def led(index, colour):
    return block('cn_rgb_matrix_set', {'led': index, 'color': colour})


def wait(value):
    return block('cn_wait', inputs={'SECONDS': number(value)})


def compare(name, op, value):
    return block('logic_compare', {'OP': op}, {'A': variable(name), 'B': number(value)})


def conditional(branches, otherwise):
    inputs = {'ELSE': otherwise}
    for index, (condition, statements) in enumerate(branches):
        inputs['IF' + str(index)] = condition
        inputs['DO' + str(index)] = statements
    return block('controls_if', inputs=inputs, extraState={'elseIfCount': len(branches) - 1, 'hasElse': True})


def display(name):
    return block('cn_seven_segment_display_value', {'device': "'STANDALONE'"}, {'value': variable(name)})


def save(filename, name, start, loop, variables=()):
    value = {'blocks': {'languageVersion': 0, 'blocks': [
        block('cn_event_start', inputs={'DO': start}, x=35, y=35),
        block('cn_event_loop', inputs={'DO': loop}, x=35, y=350)
    ]}, 'codynick_execution': {'target': 'simulator'}, 'codynick_design': {'name': name}}
    if variables:
        value['variables'] = [{'name': item, 'id': item} for item in variables]
    (DEST / filename).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


save('01_temperature_monitor.codynick', 'Temperature Monitor',
     chain(block('dash_clear'), create('gauge', 'temperature', 'Temperature (C)'),
           create('graph', 'history', 'Temperature History')),
     chain(assign('temperature', block('cn_temperature_read')), display('temperature'),
           update('temperature', variable('temperature')),
           block('dash_append', {'NAME': 'history'}, {'VALUE': variable('temperature')}), wait(1)), ['temperature'])

save('02_temperature_traffic_light.codynick', 'Temperature Traffic Light',
     chain(block('dash_clear'), create('gauge', 'temperature', 'Temperature (C)')),
     chain(assign('temperature', block('cn_temperature_read')), display('temperature'),
           update('temperature', variable('temperature')),
           conditional([(compare('temperature', 'LT', 20), led(6, '#0000FF')),
                        (compare('temperature', 'LTE', 30), led(6, '#00FF00'))], led(6, '#FF0000')), wait(0.5)), ['temperature'])

save('03_parking_assistant.codynick', 'Parking Assistant',
     chain(block('dash_clear'), create('gauge', 'distance', 'Distance (cm)'),
           block('dash_range', {'NAME': 'distance', 'MIN': 0, 'MAX': 200})),
     chain(assign('distance', block('cn_ultrasonic_read', {'device': "'STANDALONE'"})),
           update('distance', variable('distance')),
           conditional([(compare('distance', 'LT', 20), led(6, '#FF0000'))], led(6, '#00FF00')), wait(0.2)), ['distance'])

def direction(label, index, colour):
    return chain(led(index, colour), update('joystick', block('text', {'TEXT': label}), 'info'))

branches = [(block('cn_joystick_click', {'device': "'CJP'"}), direction('Pressed', 6, '#FFFFFF'))]
for name, index, colour in [('up', 13, '#0000FF'), ('down', 1, '#FFFF00'), ('left', 8, '#00FFFF'), ('right', 4, '#FF0000')]:
    branches.append((block('cn_joystick_position', {'device': "'CJP'", 'pos': repr(name)}), direction(name.title(), index, colour)))
save('04_joystick_status.codynick', 'Joystick Status',
     chain(block('dash_clear'), create('info', 'joystick', 'Joystick Direction')),
     chain(block('cn_rgb_matrix_clear'), conditional(branches, update('joystick', block('text', {'TEXT': 'Neutral'}), 'info')), wait(0.1)))
print('Generated four simulation/dashboard projects in', DEST)
