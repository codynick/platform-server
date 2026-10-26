import json
from pathlib import Path
import shutil
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node required')
class DashboardBlocksTests(unittest.TestCase):
    def test_generated_runtime_and_statements(self):
        script = """const fs=require('fs'),vm=require('vm');const c=vm.createContext({});vm.runInContext(fs.readFileSync('upstream/components/ide/blocks/dashboard.js','utf8')+';globalThis.d=DashboardBlocks',c); const block={type:'dash_set',getFieldValue:()=> 'a"b'};console.log(JSON.stringify({runtime:c.d.initialization(),statement:c.d.statement(block,()=> '42'),category:c.d.category()}));"""
        result = json.loads(subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True))
        self.assertEqual(result['category']['name'], 'Dashboard')
        self.assertIn('a\\"b', result['statement'])
        class Card:
            def __init__(self, kind, title, **settings):
                self.type, self.title = kind, title
                self.__dict__.update(settings)
            def set(self, value): self.value = value
            def save(self): pass
            def delete(self): self.deleted = True
        module = types.ModuleType('Dashboard')
        module.Card = Card
        module.clear = lambda: None
        with patch.dict(sys.modules, Dashboard=module):
            state = {}
            exec(result['runtime'], state)
            create, append = state['_dashboard_create'], state['_dashboard_append']
            create('history', 'graph', 'History')
            self.assertFalse(state['_dashboard_widgets']['history'].auto_delete)
            state['_dashboard_limit']('history', 2)
            for value in [0, 1, 2, None, float('nan')]: append('history', value)
            self.assertEqual(state['_dashboard_histories']['history'], [{'x': 2, 'y': 1.0}, {'x': 3, 'y': 2.0}])
            with self.assertRaisesRegex(RuntimeError, 'Create dashboard widget'):
                append('missing', 1)
            create('counter', 'info', 'Counter')
            card = state['_dashboard_widgets']['counter']
            self.assertEqual((card.font_size, card.horizontal_alignment, card.vertical_alignment), (32, 'center', 'center'))
            self.assertFalse(hasattr(state['_dashboard_widgets']['history'], 'font_size'))
            with self.assertRaisesRegex(RuntimeError, 'graph widget'):
                append('counter', 1)
