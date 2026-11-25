"""Routing checks only: mocked Ollama, temporary SQLite, no inference or benchmark."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import requests

ROOT = Path(__file__).resolve().parents[1]
TMP = tempfile.TemporaryDirectory()
os.environ.update(DATA_DIR=str(Path(TMP.name)/'data'), LOG_DIR=str(Path(TMP.name)/'logs'),
                  OLLAMA_MODEL='qwen2.5:7b', TRIAGE_MODE='cascade', CASCADE_SETTING='strict')
spec = importlib.util.spec_from_file_location('triage_under_test', ROOT/'service/app.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def answer(category):
    r = Mock()
    r.json.return_value = {'done': True, 'message': {'content': json.dumps({'category': category})},
                           'load_duration': 1000000}
    return r


class CascadeTests(unittest.TestCase):
    def setUp(self):
        a.TRIAGE_MODE = 'cascade'; a.CASCADE_SETTING = 'strict'; a.PUBLIC_MODEL = 'cascade-strict'
        self.client = a.app.test_client()

    def last_log(self):
        return json.loads((Path(TMP.name)/'logs/requests.jsonl').read_text().splitlines()[-1])

    def post(self):
        # Synthetic input is never sent to a real model.
        return self.client.post('/tickets', json={'narrative': 'mock-only routing test'})

    @patch.object(a.requests, 'post')
    def test_strict_accepts_one_call(self, call):
        call.return_value = answer('Mortgage')
        r = self.post()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(r.json['model'], 'cascade-strict')
        log = self.last_log()
        self.assertFalse(log['escalated']); self.assertEqual(log['final_model'], a.SMALL_MODEL)
        self.assertEqual(call.call_args.kwargs['json']['messages'][0]['content'], a.PROMPT)
        self.assertEqual(call.call_args.kwargs['json']['options'], {'temperature': 0, 'num_gpu': 0})

    @patch.object(a.requests, 'post')
    def test_strict_escalates_and_stores_large_answer(self, call):
        call.side_effect = [answer('Consumer loan'), answer('Debt collection')]
        r = self.post()
        self.assertEqual(r.json['category'], 'Debt collection'); self.assertEqual(call.call_count, 2)
        self.assertEqual([c.kwargs['json']['model'] for c in call.call_args_list], [a.SMALL_MODEL,a.LARGE_MODEL])
        log=self.last_log()
        self.assertTrue(log['escalated']); self.assertEqual(log['small_prediction'], 'Consumer loan')
        self.assertEqual(log['final_model'], a.LARGE_MODEL); self.assertEqual(len(log['model_calls']), 2)
        self.assertLessEqual(call.call_args.kwargs['timeout'][1], a.MODEL_TIMEOUT)
        self.assertTrue(all(x['duration_ms'] is not None for x in log['model_calls']))

    @patch.object(a.requests, 'post')
    def test_relaxed_accepts_consumer_loan(self, call):
        a.CASCADE_SETTING='relaxed';a.PUBLIC_MODEL='cascade-relaxed';call.return_value=answer('Consumer loan')
        self.assertEqual(self.post().status_code,201);self.assertEqual(call.call_count,1)

    @patch.object(a.requests, 'post')
    def test_single_mode_preserved(self, call):
        a.TRIAGE_MODE='single';a.PUBLIC_MODEL=a.OLLAMA_MODEL;call.return_value=answer('Credit reporting')
        r=self.post();self.assertEqual(r.json['model'],a.OLLAMA_MODEL)
        self.assertEqual(call.call_count,1);self.assertFalse(self.last_log()['escalated'])

    @patch.object(a.requests, 'post')
    def test_invalid_small_output_escalates(self, call):
        call.side_effect=[answer('not a category'),answer('Credit card')]
        self.assertEqual(self.post().status_code,201)
        self.assertEqual(self.last_log()['escalation_reason'],'invalid_small_output')

    @patch.object(a.requests, 'post')
    def test_large_failure_does_not_store(self, call):
        before=self.client.get('/stats').json['total']
        call.side_effect=[answer('Credit reporting'),requests.exceptions.Timeout()]
        self.assertEqual(self.post().status_code,504)
        log=self.last_log();self.assertTrue(log['escalated']);self.assertIsNone(log['final_model'])
        self.assertEqual(self.client.get('/stats').json['total'],before)

    @patch.object(a.requests, 'post')
    def test_transport_failure_not_retried(self, call):
        call.side_effect=requests.exceptions.ConnectionError()
        self.assertEqual(self.post().status_code,502);self.assertEqual(call.call_count,1)

    @patch.object(a.requests, 'post')
    def test_invalid_input_no_model_call(self, call):
        self.assertEqual(self.client.post('/tickets',json={'narrative':''}).status_code,400)
        call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
