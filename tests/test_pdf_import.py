import unittest
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bank_update import make_handler
from pdf_import import parse_pages, parse_pdf


class PdfImportTests(unittest.TestCase):
    def test_reading_questions_options_and_answer_key(self):
        page = """IELTS READING
A passage about a coastal marsh.
Questions 1-3
1. What was built beside the river?
A. A railway
B. A public marsh
2) The site used to be a loading yard.
3. Name the material removed from the site.
Answer Key
1 B
2 TRUE
3 concrete
"""
        result = parse_pages([page], "reading", "Sample")
        self.assertEqual([q["number"] for q in result["questions"]], [1, 2, 3])
        self.assertEqual(result["questions"][0]["options"], ["A. A railway", "B. A public marsh"])
        self.assertEqual(result["questions"][0]["answer"], "B")
        self.assertEqual(result["questions"][2]["answer"], "concrete")
        self.assertNotIn("Answer Key", result["referenceText"])

    def test_writing_tasks_are_separate_and_unscored(self):
        result = parse_pages(["Writing Task 1\nDescribe the chart.\nTask 2\nDiscuss both views."], "writing", "Writing")
        self.assertEqual(len(result["questions"]), 2)
        self.assertIn("Describe the chart", result["questions"][0]["prompt"])
        self.assertEqual(result["questions"][1]["answer"], "")

    def test_text_pdf_round_trip_and_scanned_pdf_error(self):
        try:
            import pymupdf
        except ImportError:
            self.skipTest("optional PyMuPDF not installed")
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((50, 50), "Questions 1-2\n1. Choose A.\n2. Choose B.")
        data = document.tobytes()
        document.close()
        result = parse_pdf(data, "listening", "demo.pdf")
        self.assertEqual(result["title"], "demo")
        self.assertEqual([q["number"] for q in result["questions"]], [1, 2])

        document = pymupdf.open()
        document.new_page()
        blank = document.tobytes()
        document.close()
        with self.assertRaisesRegex(ValueError, "OCR"):
            parse_pdf(blank, "reading", "scan.pdf")

    def test_local_import_endpoint(self):
        try:
            import pymupdf
        except ImportError:
            self.skipTest("optional PyMuPDF not installed")
        document = pymupdf.open()
        document.new_page().insert_text((50, 50), "Questions 1-2\n1. First prompt.\n2. Second prompt.")
        data = document.tobytes()
        document.close()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/api/import-pdf"
        headers = {"Content-Type": "application/pdf", "X-IELTS-Skill": "reading"}
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url, data=data, headers=headers), timeout=3)
            self.assertEqual(error.exception.code, 403)
            headers["Origin"] = f"http://127.0.0.1:{server.server_port}"
            with urlopen(Request(url, data=data, headers=headers), timeout=3) as response:
                result = json.load(response)
            self.assertEqual(len(result["questions"]), 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
