import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import install


class DemoSeedingTests(unittest.TestCase):
    def test_load_payloads_and_preserved_designs(self):
        examples = Path(__file__).resolve().parents[1] / 'upstream/components/examples/blockly'
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'designs'
            install.seed_demo_designs(directory, examples)
            designs = sorted(directory.glob('*.json'))
            self.assertEqual(len(designs), 4)
            for path in designs:
                payload = json.loads(path.read_text())
                self.assertEqual(path.stem, hashlib.sha256(payload['name'].encode()).hexdigest())
                self.assertEqual(payload['workspace']['codynick_design']['name'], payload['name'])
                self.assertEqual(payload['workspace']['codynick_execution']['target'], 'simulator')
            designs[0].write_text('{"my_saved_changes":true}')
            (directory / 'student.json').write_text('{"my_project":true}')
            install.seed_demo_designs(directory, examples)
            self.assertEqual(designs[0].read_text(), '{"my_saved_changes":true}')
            self.assertEqual((directory / 'student.json').read_text(), '{"my_project":true}')
