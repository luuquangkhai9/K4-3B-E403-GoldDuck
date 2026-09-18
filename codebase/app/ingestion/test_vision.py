"""Vision acceptance tests on actual synthetic PDF pages, without paid calls."""

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from unittest.mock import Mock, patch

import pymupdf

from .ingest import ingest_pdfs
from .parser import parse_pdf
from .vision import VisionAdapter, VisionConfig, VisionEnricher, image_area_ratio


class VisionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pdf_dir = self.root / "pdf"
        self.pdf_dir.mkdir()
        self.path = self.pdf_dir / "slides.pdf"
        self.output = self.root / "index" / "slides.json"
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=600, height=400)
            page.insert_textbox((20, 20, 580, 380), "Gradient descent updates model parameters. " * 12)
            page = pdf.new_page(width=600, height=400)
            pixels = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), False)
            pixels.clear_with(150)
            page.insert_image((0, 0, 600, 400), stream=pixels.tobytes("png"))
            page.insert_text((20, 40), "CNN")
            pdf.save(self.path)
        self.analysis = {"summary": "Visible CNN diagram", "concepts": ["CNN"],
                         "relationships": ["Input -> Convolution"], "visible_text_not_in_pdf": ["Input"]}
        self.adapter = Mock()
        self.adapter.analyze.return_value = self.analysis
        self.config = VisionConfig(enabled=True, model="test-model")

    def records(self):
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_selective_rendering_and_second_ingestion_cache(self):
        with patch.object(pymupdf.Page, "get_pixmap", autospec=True, side_effect=pymupdf.Page.get_pixmap) as render:
            ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config, vision_adapter=self.adapter)
            self.assertEqual(render.call_count, 1)
        normal, visual = self.records()
        self.assertEqual(normal["visual_analysis"]["status"], "skipped")
        self.assertEqual(normal["retrieval_text"], normal["text"])
        self.assertEqual(visual["visual_analysis"]["status"], "success")
        self.assertIn("Input -> Convolution", visual["retrieval_text"])
        self.assertIn("Visible text: Input", visual["retrieval_text"])
        self.assertEqual(visual["visual_analysis"]["image_area_ratio"], 1.0)
        ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config, vision_adapter=self.adapter)
        self.assertEqual(self.adapter.analyze.call_count, 1)
        self.assertTrue(self.records()[1]["visual_analysis"]["cached"])

    def test_disabled_preserves_v1_records_without_render_or_api(self):
        with patch.object(pymupdf.Page, "get_pixmap", side_effect=AssertionError("Must not render")):
            ingest_pdfs(self.pdf_dir, self.output, vision_config=VisionConfig(), vision_adapter=self.adapter)
        _, expected = parse_pdf(self.path)
        self.assertEqual(self.records(), expected)
        self.adapter.analyze.assert_not_called()

    def test_api_failure_and_invalid_json_preserve_native_text(self):
        for response in (RuntimeError("timeout"), {"summary": "bad"}):
            with self.subTest(response=response):
                self.adapter.analyze.side_effect = response if isinstance(response, Exception) else None
                self.adapter.analyze.return_value = response
                result = ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config, vision_adapter=self.adapter)
                slide = self.records()[1]
                self.assertEqual(slide["visual_analysis"]["status"], "failed")
                self.assertEqual(slide["retrieval_text"], slide["text"])
                self.assertEqual(result["vision"], {"skipped": 1, "failed": 1})

    def test_parallel_requests_keep_pdf_rendering_on_caller_and_wait_before_write(self):
        with pymupdf.open(self.path) as source, pymupdf.open() as pdf:
            pdf.insert_pdf(source)
            pdf.insert_pdf(source, from_page=1, to_page=1)
            replacement = self.root / "replacement.pdf"
            pdf.save(replacement)
        replacement.replace(self.path)
        barrier = threading.Barrier(2)
        caller = threading.get_ident()
        render = pymupdf.Page.get_pixmap

        def checked_render(page, *args, **kwargs):
            self.assertEqual(threading.get_ident(), caller)
            return render(page, *args, **kwargs)

        def analyze(image, text):
            self.assertNotEqual(threading.get_ident(), caller)
            barrier.wait(timeout=5)
            return self.analysis

        self.adapter.analyze.side_effect = analyze
        with patch.object(pymupdf.Page, "get_pixmap", checked_render):
            result = ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config,
                                 vision_adapter=self.adapter, vision_workers=2)
        self.assertEqual(result["vision"], {"skipped": 1, "success": 2})
        self.assertTrue(all("Input -> Convolution" in slide["retrieval_text"] for slide in self.records()[1:]))
        ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config,
                    vision_adapter=self.adapter, vision_workers=2)
        self.assertEqual(self.adapter.analyze.call_count, 2)

    def test_adapter_retries_transient_http_errors_but_not_invalid_credentials(self):
        config = VisionConfig(enabled=True, api_key="fake-key", model="configured-model")
        response = Mock()
        response.read.return_value = json.dumps({"choices": [{"message": {"content": json.dumps(self.analysis)}}]}).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        for status, calls in ((429, 2), (401, 1)):
            with self.subTest(status=status), patch("app.ingestion.vision.time.sleep"), patch(
                "app.ingestion.vision.urlopen", side_effect=[HTTPError("url", status, "hidden", {}, None), response]
            ) as request:
                if status == 429:
                    self.assertEqual(VisionAdapter(config).analyze(b"png", "CNN"), self.analysis)
                else:
                    with self.assertRaises(HTTPError):
                        VisionAdapter(config).analyze(b"png", "CNN")
                self.assertEqual(request.call_count, calls)

    def test_low_text_without_images_is_flagged(self):
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            slide = {"slide_id": "blank", "text": ""}
            VisionEnricher(self.config, self.root / "cache", self.adapter).enrich(page, slide)
            self.assertEqual(slide["visual_analysis"]["reason"], "low_text")
            self.assertEqual(slide["visual_analysis"]["status"], "success")

    def test_cache_identity_includes_model_and_image(self):
        ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config, vision_adapter=self.adapter)
        ingest_pdfs(self.pdf_dir, self.output, vision_config=VisionConfig(enabled=True, model="other"), vision_adapter=self.adapter)
        self.assertEqual(self.adapter.analyze.call_count, 2)
        with pymupdf.open(self.path) as pdf:
            pdf[1].insert_text((20, 80), "Pooling")
            replacement = self.pdf_dir / "replacement.pdf"
            pdf.save(replacement)
        replacement.replace(self.path)
        ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config, vision_adapter=self.adapter)
        self.assertEqual(self.adapter.analyze.call_count, 3)

    def test_corrupt_cache_is_replaced(self):
        ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config, vision_adapter=self.adapter)
        cache = next((self.output.parent / "vision").glob("*.json"))
        cache.write_text("not JSON", encoding="utf-8")
        ingest_pdfs(self.pdf_dir, self.output, vision_config=self.config, vision_adapter=self.adapter)
        self.assertEqual(self.adapter.analyze.call_count, 2)
        self.assertEqual(json.loads(cache.read_text(encoding="utf-8")), self.analysis)

    def test_overlapping_images_are_not_double_counted(self):
        with pymupdf.open(self.path) as pdf:
            page = pdf[1]
            with patch.object(pymupdf.Page, "get_image_info", return_value=[{"bbox": (0, 0, 300, 400)}] * 2):
                self.assertEqual(image_area_ratio(page), 0.5)

    def test_adapter_sends_strict_schema_and_visible_only_prompt(self):
        response = Mock()
        response.read.return_value = json.dumps({"choices": [{"message": {"content": json.dumps(self.analysis)}}]}).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        config = VisionConfig(enabled=True, api_key="fake-key", model="configured-model")
        with patch("app.ingestion.vision.urlopen", return_value=response) as request:
            self.assertEqual(VisionAdapter(config).analyze(b"png", "CNN"), self.analysis)
        payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload["model"], "configured-model")
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertIn("Do not add outside knowledge", payload["messages"][0]["content"])

    def test_invalid_environment_disables_vision_without_failing_ingestion(self):
        for override in ({"VISION_TEXT_THRESHOLD": "-1"},
                         {"VISION_IMAGE_RATIO_THRESHOLD": "nan"},
                         {"VISION_IMAGE_RATIO_THRESHOLD": "1.5"},
                         {"VISION_TIMEOUT": "inf"}, {"VISION_TIMEOUT": "0"}):
            with self.subTest(override=override), patch.dict(os.environ, {"VISION_ENABLED": "true", **override}):
                result = ingest_pdfs(self.pdf_dir, self.output, vision_adapter=self.adapter)
                self.assertEqual(result["slides"], 2)
                self.assertTrue(all("visual_analysis" not in slide for slide in self.records()))
        self.adapter.analyze.assert_not_called()

    def test_environment_normalizes_switch_and_provider(self):
        with patch.dict(os.environ, {"VISION_ENABLED": " on ", "VISION_PROVIDER": " OpenAI ",
                                    "VISION_TEXT_THRESHOLD": "120", "VISION_IMAGE_RATIO_THRESHOLD": "0.4", "VISION_TIMEOUT": "30"}):
            config = VisionConfig.from_env()
        self.assertTrue(config.enabled)
        self.assertEqual(config.provider, "openai")


if __name__ == "__main__":
    unittest.main()
