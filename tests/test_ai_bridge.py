from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import ai_bridge
import speech_analysis
from bank_update import make_handler


class AiBridgeTests(unittest.TestCase):
    def test_current_season_feedback_uses_bundled_questions_only(self):
        seasonal = ai_bridge.read_data("season-content.json")
        reading = seasonal["reading"][0]
        original = ai_bridge.read_data
        def same_season(name):
            data = original(name)
            if name == "public-index.json":
                data["season"]["id"] = seasonal["seasonId"]
            return data
        with patch.object(ai_bridge, "read_data", side_effect=same_season):
            case = ai_bridge.build_case({"kind": "season-reading", "itemId": reading["id"],
                                         "questionId": reading["questions"][0]["id"],
                                         "answer": "wrong", "correctAnswer": "forged"})
            writing = seasonal["writing"][0]
            writing_case = ai_bridge.build_case({"kind": "season-writing", "itemId": writing["id"],
                                                 "answer": "I believe that practice can improve artistic skills. " * 4,
                                                 "question": "forged"})
            with self.assertRaises(ValueError):
                ai_bridge.build_case({"kind": "season-listening", "itemId": "missing",
                                      "questionId": "1", "answer": "wrong"})
        self.assertEqual(case["correctAnswer"], reading["questions"][0]["answer"])
        self.assertTrue(case["passageEvidence"])
        self.assertEqual(writing_case["question"], writing["prompt"])
        self.assertEqual(writing_case["kind"], "writing")
        def shifted(name):
            data = original(name)
            if name == "public-index.json":
                data["season"]["id"] = "2027-01_2027-04"
            return data
        with patch.object(ai_bridge, "read_data", side_effect=shifted):
            with self.assertRaisesRegex(ValueError, "已换期"):
                ai_bridge.build_case({"kind": "season-writing", "itemId": writing["id"],
                                      "answer": "A long enough practice answer. " * 5})

    def test_current_season_feedback_endpoint_uses_trusted_prompt(self):
        seasonal = ai_bridge.read_data("season-content.json")
        writing = seasonal["writing"][0]
        original = ai_bridge.read_data
        def same_season(name):
            data = original(name)
            if name == "public-index.json":
                data["season"]["id"] = seasonal["seasonId"]
            return data
        feedback = {"summary": "practice", "estimatedBand": 6.5, "criteria": [],
                    "correction": "x", "nextStep": "y", "limitations": "estimate"}
        with patch.object(ai_bridge, "read_data", side_effect=same_season), \
             patch("ai_bridge.run_codex", return_value=feedback) as codex:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/api/feedback"
                body = json.dumps({"kind": "season-writing", "itemId": writing["id"],
                                   "answer": "Practice can develop artistic skills over time. " * 4,
                                   "question": "forged"}).encode()
                request = Request(url, data=body, headers={
                    "Content-Type": "application/json",
                    "Origin": f"http://127.0.0.1:{server.server_port}"})
                with urlopen(request, timeout=3) as response:
                    self.assertEqual(json.load(response)["feedback"]["summary"], "practice")
                self.assertEqual(codex.call_args.args[0]["question"], writing["prompt"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_cases_use_local_question_and_answer_key(self):
        case = ai_bridge.build_case({"kind": "reading", "questionNumber": 1,
                                     "answer": "wrong", "correctAnswer": "forged"})
        self.assertEqual(case["candidateAnswer"], "wrong")
        self.assertNotEqual(case["correctAnswer"], "forged")
        self.assertTrue(case["passageEvidence"])
        with self.assertRaises(ValueError):
            ai_bridge.build_case({"kind": "writing", "taskId": "W1", "answer": "short"})

    def test_speaking_is_transcript_only(self):
        seasonal = ai_bridge.read_data("season-content.json")
        authored = seasonal["speaking"][0]
        topic = {"id": authored["sourceId"], "url": authored["sourceUrl"],
                 "title": authored["sourceTitle"], "part": authored["part"]}
        original = ai_bridge.read_data
        def practice_topic(name):
            if name == "public-index.json":
                return {"season": {"id": seasonal["seasonId"]}, "speaking": [topic]}
            return original(name)
        with patch.object(ai_bridge, "read_data", side_effect=practice_topic):
            case = ai_bridge.build_case({"kind": "speaking", "topicId": topic["id"],
                                         "answer": "I would like to explain my answer in more detail."})
        self.assertIn("candidateTranscript", case)
        self.assertTrue(case["practiceQuestions"])
        self.assertNotIn("audioBytes", case)
        self.assertIn("Pronunciation", ai_bridge.prompt_for(case))

    def test_recording_case_uses_local_timing_and_keeps_pronunciation_unscored(self):
        topics = ai_bridge.read_data("public-index.json")["speaking"]
        evidence = {"transcript": "I really enjoy reading books because they help me relax after work.",
                    "durationSeconds": 14.2, "speechSeconds": 10.1, "wordCount": 13,
                    "wordsPerMinute": 77, "pauseCount": 2, "longPauseCount": 1}
        case = ai_bridge.build_spoken_case(topics[0]["id"], evidence)
        self.assertEqual(case["audioTiming"]["pauseCount"], 2)
        self.assertIn("Pronunciation in criteria with estimate null", ai_bridge.prompt_for(case))
        self.assertNotIn("audioBytes", case)

    def test_local_transcriber_extracts_approximate_pauses(self):
        word = lambda text, start, end: SimpleNamespace(word=text, start=start, end=end)
        segments = [SimpleNamespace(text="I like books because they are interesting.",
                                    start=1.0, end=5.0,
                                    words=[word("I", 1.0, 1.2), word("like", 1.2, 1.5),
                                           word("books", 3.1, 3.5)])]
        model = SimpleNamespace(transcribe=lambda *_args, **_kwargs:
                                (iter(segments), SimpleNamespace(duration=6.0)))
        with patch.object(speech_analysis, "speech_model", return_value=model):
            evidence = speech_analysis.transcribe_audio(b"fake audio", "audio/webm;codecs=opus")
        self.assertEqual(evidence["pauseCount"], 1)
        self.assertEqual(evidence["longPauseCount"], 1)
        self.assertEqual(evidence["durationSeconds"], 6.0)
        with self.assertRaises(ValueError):
            speech_analysis.transcribe_audio(b"fake audio", "text/plain")

    def test_audio_api_sends_recording_evidence_to_codex(self):
        topic = ai_bridge.read_data("public-index.json")["speaking"][0]["id"]
        evidence = {"transcript": "I really enjoy reading books because they help me relax after work.",
                    "durationSeconds": 14.2, "speechSeconds": 10.1, "wordCount": 13,
                    "wordsPerMinute": 77, "pauseCount": 2, "longPauseCount": 1}
        feedback = {"summary": "ok", "estimatedBand": 6.5, "criteria": [],
                    "correction": "x", "nextStep": "y", "limitations": "partial estimate"}
        with patch("speech_analysis.transcribe_audio", return_value=evidence) as transcribe, \
             patch("ai_bridge.run_codex", return_value=feedback) as codex:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/api/speaking-audio"
            try:
                headers = {"Content-Type": "audio/webm", "Origin": f"http://127.0.0.1:{server.server_port}",
                           "X-IELTS-Topic": topic}
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url, data=b"fake audio", headers={"Content-Type": "audio/webm"}), timeout=3)
                self.assertEqual(error.exception.code, 403)
                with urlopen(Request(url, data=b"fake audio", headers=headers), timeout=3) as response:
                    result = json.load(response)
                transcribe.assert_called_once_with(b"fake audio", "audio/webm")
                self.assertEqual(codex.call_args.args[0]["audioTiming"]["pauseCount"], 2)
                self.assertEqual(result["transcript"], evidence["transcript"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_feedback_shape_rejects_invalid_band(self):
        good = {"summary": "ok", "estimatedBand": None, "criteria": [], "correction": "x",
                "nextStep": "y", "limitations": "practice only"}
        self.assertEqual(ai_bridge.validate_feedback(good)["summary"], "ok")
        with self.assertRaises(ValueError):
            ai_bridge.validate_feedback({**good, "estimatedBand": 6.3})

    def test_speaking_feedback_never_assigns_pronunciation_band(self):
        feedback = {"summary": "ok", "estimatedBand": 6.5,
                    "criteria": [{"name": "Pronunciation", "estimate": 8.0, "feedback": "sounds clear"}],
                    "correction": "x", "nextStep": "y", "limitations": "practice"}
        result = ai_bridge.enforce_speaking_limits({"kind": "speaking", "audioTiming": {}}, feedback)
        self.assertIsNone(result["criteria"][0]["estimate"])
        self.assertIn("缺少发音维度", result["limitations"])

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
