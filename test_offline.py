import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from history import append_history
import knowledge_db
from modulos.smb_enumerator import SMBEnumerator


class HistoryTests(unittest.TestCase):
    def test_appends_without_losing_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            append_history(path, [{"demo": 1}])
            append_history(path, [{"demo": 2}])
            self.assertEqual(json.loads(path.read_text(encoding="utf8")), [{"demo": 1}, {"demo": 2}])

    def test_corrupt_history_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            path.write_text("invalid original", encoding="utf8")
            with self.assertRaises(json.JSONDecodeError):
                append_history(path, [{"demo": 1}])
            self.assertEqual(path.read_text(encoding="utf8"), "invalid original")

    def test_wrong_shape_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            path.write_text('{"demo": 1}', encoding="utf8")
            with self.assertRaises(ValueError):
                append_history(path, [{"demo": 2}])
            self.assertEqual(json.loads(path.read_text(encoding="utf8")), {"demo": 1})

    def test_failed_replace_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            path.write_text('[{"demo": 1}]', encoding="utf8")
            with patch("history.os.replace", side_effect=OSError("synthetic failure")):
                with self.assertRaises(OSError): append_history(path, [{"demo": 2}])
            self.assertEqual(json.loads(path.read_text(encoding="utf8")), [{"demo": 1}])
            self.assertEqual(list(Path(folder).iterdir()), [path])


class KnowledgeTests(unittest.TestCase):
    def test_import_has_no_client(self):
        self.assertIsNone(knowledge_db.client)

    def test_default_paths_relative_to_module(self):
        self.assertEqual(knowledge_db.DOCS_PATH, Path(knowledge_db.__file__).parent / "docs")

    def test_heading_at_start_and_empty_sections(self):
        records = knowledge_db.markdown_records("demo", "## First\nBody\n## Empty\n## Second\nText")
        self.assertEqual(records, [("First", "Body"), ("Second", "Text")])

    def test_no_sections_is_not_a_record(self):
        self.assertEqual(knowledge_db.markdown_records("demo", "Introduction only"), [])

    def test_path_traversal_topic_rejected_without_client(self):
        with self.assertRaises(ValueError): knowledge_db.get_collection("../private")

    def test_query_count_bounded(self):
        collection = Mock()
        collection.count.return_value = 1
        collection.query.return_value = {"ids": [[]]}
        with patch.object(knowledge_db, "get_collection", return_value=collection), contextlib.redirect_stdout(io.StringIO()):
            knowledge_db.query_error("demo", "synthetic query", n_results=5)
        collection.query.assert_called_once_with(query_texts=["synthetic query"], n_results=1)


class PlaceholderTests(unittest.TestCase):
    def test_smb_placeholder_does_not_report_success(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = SMBEnumerator("synthetic.invalid").run()
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error_message"])

    def test_all_sources_parse_without_execution(self):
        import ast
        root = Path(__file__).resolve().parent
        for source in root.rglob("*.py"):
            if set(source.relative_to(root).parts) & {".venv", "__pycache__"}: continue
            with self.subTest(source=str(source.relative_to(root))):
                ast.parse(source.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
