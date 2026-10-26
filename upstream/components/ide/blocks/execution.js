'use strict';
const ExecutionTarget = (() => {
  const select = () => document.getElementById('executionTarget');
  function initialization(blocks) {
    if (select().value !== 'simulator') return 'cody = CN()';
    const gadgets = new Set();
    for (const block of blocks) {
      const type = block.type, device = block.getFieldValue('device');
      let gadget;
      if (type.startsWith('cn_rgb_matrix_') || type.startsWith('cn_sound_')) gadget = 'cjp';
      else if (type.startsWith('cn_led_matrix_')) gadget = 'matrix';
      else if (type === 'cn_temperature_read') gadget = 'temperature';
      else if (type === 'cn_soil_read') gadget = 'soil';
      else if (type.startsWith('cn_wifi_') || type.startsWith('cn_iot_')) gadget = 'wifi';
      else if (type.startsWith('cn_joystick_')) {
        if (["'CJP'", '5'].includes(device)) gadget = 'cjp';
        else if (["'STANDALONE'", '0'].includes(device)) gadget = 'joystick';
      } else if (['cn_seven_segment_display', 'cn_ultrasonic_read'].includes(type)) {
        if (["'STANDALONE'", '0'].includes(device)) gadget = type === 'cn_seven_segment_display' ? 'seven' : 'ultrasonic';
      } else if (type === 'cn_log') continue;
      if (!gadget) return 'raise RuntimeError(' + JSON.stringify('Block ' + type + ' / device ' + (device || '') + ' is not supported in Simulator mode. Choose Hardware or remove this block.') + ')';
      gadgets.add(gadget);
    }
    return 'cody = Simulator(required_gadgets=' + JSON.stringify([...gadgets].sort()) + ')';
  }
  function initialize() {
    Blockly.serialization.registry.register('codynick_execution', {
      priority: 6,
      save: () => ({target: select().value}),
      load: data => {select().value = data?.target === 'simulator' ? 'simulator' : 'hardware';},
      clear: () => {select().value = 'hardware';}
    });
    select().addEventListener('change', () => {updatePythonPreview(true);scheduleSave();});
  }
  return {initialize, initialization};
})();
