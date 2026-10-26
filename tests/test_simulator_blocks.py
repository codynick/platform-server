import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / 'upstream/components/simulator'
sys.path.insert(0, str(directory))
spec = importlib.util.spec_from_file_location('block_sim_server', directory / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
spec = importlib.util.spec_from_file_location('block_sim_bridge', ROOT / 'upstream/components/client/CodyNickSimulator.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class SimulatorBlocksTests(unittest.TestCase):
    def test_missing_gadget_reports_rerun_without_locking_scene(self):
        state = server.State()
        with self.assertRaisesRegex(ValueError, 'Add LED matrix to the simulation space, then re-run the app'):
            state.command({'action':'check_gadgets','gadgets':['matrix']})
        self.assertIsNone(state.session)
        scene = dict(state.scene, gadgets=dict(state.scene['gadgets'], matrix={'x':100,'y':100}))
        state.command({'action':'scene','scene':scene})
        self.assertTrue(state.command({'action':'check_gadgets','gadgets':['matrix']})['ok'])
        self.assertEqual(state.error, '')

    def test_bad_requirements_do_not_allocate_a_session(self):
        for gadgets in ('matrix', ['unknown'], [1], ['matrix'] * 9):
            state = server.State()
            with self.assertRaises(ValueError):
                state.command({'action':'check_gadgets','gadgets':gadgets})
            self.assertIsNone(state.session)

    def test_bridge_checks_before_opening_or_starting_heartbeat(self):
        with patch.object(bridge.Path, 'read_text', return_value='a'*64), patch.object(bridge.Simulator, '_request', side_effect=RuntimeError('Add LED matrix, then re-run')) as request, patch.object(bridge.threading, 'Thread') as thread:
            with self.assertRaises(RuntimeError):
                bridge.Simulator(required_gadgets=['matrix'])
            request.assert_called_once_with('check_gadgets', gadgets=['matrix'])
            thread.assert_not_called()
