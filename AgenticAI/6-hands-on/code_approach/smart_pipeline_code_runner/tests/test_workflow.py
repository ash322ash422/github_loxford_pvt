import tempfile
import unittest
from pathlib import Path
from smart_pipeline.reference_pipeline import process
from smart_pipeline.tools.inventory import scan_directory, safe_path
from smart_pipeline.tools.profiling import profile_csv
from smart_pipeline.tools.validation import validate_outputs
from smart_pipeline.tools.archive import archive_processed_files, restore
from smart_pipeline.tools.execution import execute_script


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.run = self.root / 'run'
        self.source.mkdir()
        (self.run / 'inputs').mkdir(parents=True)
        (self.run / 'outputs').mkdir()
        self.content = 'Order ID,Order Date,Category,Revenue\na,2026-01-01,Books,10.00\na,2026-01-01,Books,10.00\nb,bad,Books,2\n'
        for folder in [self.source, self.run / 'inputs']:
            (folder / 'sales.csv').write_text(self.content)
        self.plan = {'files': ['sales.csv']}

    def state(self):
        return dict(run_id='test', run_root=str(self.run), input_root=str(self.source),
                    processing_plan=self.plan, file_inventory=scan_directory(self.source),
                    validation_result={'valid': True})

    def test_reconciliation_and_tamper(self):
        process(self.run / 'inputs', self.run / 'outputs', self.plan)
        result = validate_outputs(self.run, self.plan)
        self.assertTrue(result['valid'], result)
        self.assertEqual((result['accepted'], result['rejected'], result['duplicates']), (1, 2, 1))
        (self.run / 'outputs' / 'summary.csv').write_text('month,category,revenue,order_count\n2026-01,Books,999,1\n')
        self.assertFalse(validate_outputs(self.run, self.plan)['valid'])

    def test_archive_repeat_restore_changed(self):
        state = self.state()
        archive = self.root / 'archive'
        first = archive_processed_files(state, archive)
        self.assertEqual(first, archive_processed_files(state, archive))
        restore(self.run, self.source)
        self.assertEqual((self.source / 'sales.csv').read_text(), self.content)
        (self.source / 'sales.csv').write_text('changed')
        with self.assertRaises(ValueError):
            restore(self.run, self.source)

    def test_changed_input_preserved(self):
        state = self.state()
        (self.source / 'sales.csv').write_text('changed')
        with self.assertRaises(ValueError):
            archive_processed_files(state, self.root / 'archive')
        self.assertTrue((self.source / 'sales.csv').exists())

    def test_malformed_incompatible_and_escape(self):
        path = self.source / 'bad.csv'
        path.write_text('a,b\n"unclosed')
        self.assertFalse(profile_csv(path, 'bad.csv')['compatible'])
        path.write_text('employee,department\na,b\n')
        self.assertFalse(profile_csv(path, 'bad.csv')['compatible'])
        with self.assertRaises(ValueError):
            safe_path(self.source, '../escape')

    def test_failed_execution_routes_to_repair(self):
        from unittest.mock import patch
        from smart_pipeline.graph import build_graph
        with patch('smart_pipeline.graph.execute_script', return_value={'exit_code': 1, 'error': 'fixture failure'}):
            graph = build_graph(None, self.root / 'archive', offline=True)
            state = graph.invoke(dict(run_id='test', run_root=str(self.root / 'newrun'),
                input_root=str(self.source), user_request='sales', errors=[], execution_attempts=0))
            self.assertEqual(state['status'], 'failed')
            self.assertTrue((self.source / 'sales.csv').exists())

    def test_two_repairs_then_success(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from smart_pipeline.graph import build_graph
        from smart_pipeline import reference_pipeline
        code = Path(reference_pipeline.__file__).read_text()
        class CodingModel:
            calls = 0
            def invoke(self, messages):
                self.calls += 1
                return SimpleNamespace(content=code)
        model = CodingModel()
        attempts = []
        def execute(run_root):
            attempts.append(run_root)
            if len(attempts) < 3:
                return {'exit_code': 1, 'error': 'intentional failure'}
            process(Path(run_root) / 'inputs', Path(run_root) / 'outputs', self.plan)
            return {'exit_code': 0, 'error': ''}
        with patch('smart_pipeline.graph.execute_script', side_effect=execute):
            state = build_graph(model, self.root / 'archive').invoke(dict(
                run_id='repair', run_root=str(self.root / 'repair'), input_root=str(self.source),
                user_request='sales', errors=[], execution_attempts=0))
        self.assertEqual(model.calls, 3)
        self.assertEqual(state['execution_attempts'], 3)
        self.assertEqual(state['status'], 'complete')


if __name__ == '__main__':
    unittest.main()
