from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import ai_bridge
from bank_update import make_handler


class AiBridgeTests(unittest.TestCase):
    def test_cases_use_local_question_and_answer_key(self):
        case = ai_bridge.build_case({"kind": "reading", "questionNumber": 1,
                                     "answer": "wrong", "correctAnswer": "forged"})
        self.assertEqual(case["candidateAnswer"], "wrong")
        self.assertNotEqual(case["correctAnswer"], "forged")
        self.assertTrue(case["passageEvidence"])
        with self.assertRaises(ValueError):
            ai_bridge.build_case({"kind": "writing", "taskId": "W1", "answer": "short"})

    def test_speaking_is_transcript_only(self):
        topics = ai_bridge.read_data("public-index.json")["speaking"]
        case = ai_bridge.build_case({"kind": "speaking", "topicId": topics[0]["id"],
                                     "answer": "I would like to explain my answer in more detail."})
        self.assertIn("candidateTranscript", case)
        self.assertNotIn("audioBytes", case)
        self.assertIn("Pronunciation", ai_bridge.prompt_for(case))

    def test_feedback_shape_rejects_invalid_band(self):
        good = {"summary": "ok", "estimatedBand": None, "criteria": [], "correction": "x",
                "nextStep": "y", "limitations": "practice only"}
        self.assertEqual(ai_bridge.validate_feedback(good)["summary"], "ok")
        with self.assertRaises(ValueError):
            ai_bridge.validate_feedback({**good, "estimatedBand": 6.3})

    def test_local_api_requires_same_origin_and_cli_is_optional(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/api/feedback"
        body = json.dumps({"kind": "reading", "questionNumber": 1, "answer": "wrong"}).encode()
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=3)
            self.assertEqual(error.exception.code, 403)
            with patch.dict(os.environ, {"IELTS_CODEX_ENABLED": "0"}):
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/capabilities", timeout=3) as response:
                    self.assertFalse(json.load(response)["codexCli"])
            request = Request(url, data=body, headers={"Content-Type": "application/json",
                                                       "Origin": f"http://127.0.0.1:{server.server_port}"})
            with patch.dict(os.environ, {"IELTS_CODEX_ENABLED": "0"}):
                with self.assertRaises(HTTPError) as error:
                    urlopen(request, timeout=3)
            self.assertEqual(error.exception.code, 503)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
