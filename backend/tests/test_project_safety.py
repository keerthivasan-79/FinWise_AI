import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class ProjectSafetyTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_no_weak_secret_defaults_in_config(self):
        config = self.read("backend/config.py")
        self.assertNotIn('"1234"', config)
        self.assertNotIn("change-this-secret-before-deployment", config)
        self.assertIn("local_secret", config)

    def test_reset_tokens_are_hidden_by_default(self):
        app = self.read("backend/app.py")
        self.assertIn("SHOW_RESET_TOKEN','false", app)
        self.assertIn("SHOW_VERIFICATION_TOKEN','false", app)

    def test_no_browser_popup_calls_in_frontend_pages(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend/src").rglob("*.jsx"))
        self.assertIsNone(re.search(r"\b(alert|prompt|confirm)\s*\(", source))

    def test_statement_undo_no_longer_bulk_deletes_legacy_rows(self):
        app = self.read("backend/app.py")
        self.assertNotIn("payment_method='Bank Statement' AND statement_import_id IS NULL", app)
        self.assertIn("statement_duplicate_exists", app)

    def test_frontend_dependencies_are_pinned(self):
        package = json.loads(self.read("frontend/package.json"))
        for name, version in package["dependencies"].items():
            self.assertNotEqual(version, "latest", name)
            self.assertRegex(version, r"^\d+\.\d+\.\d+$", name)

    def test_offline_chat_has_project_help_topics(self):
        app = self.read("backend/app.py")
        self.assertIn("FINWISE_HELP_TOPICS", app)
        self.assertIn("Multinomial Naive Bayes", app)
        self.assertIn("transfer is not income or expense", app.lower())
        self.assertIn("does not need internet", app.lower())

    def test_family_option_is_removed_from_frontend(self):
        future_hub = self.read("frontend/src/pages/FutureHub.jsx").lower()
        goals = self.read("frontend/src/pages/Goals.jsx").lower()
        assistant = self.read("frontend/src/pages/AIInsights.jsx").lower()
        self.assertNotIn('"family"', future_hub)
        self.assertNotIn("household", future_hub)
        self.assertNotIn("pendinginvites", future_hub)
        self.assertNotIn("share this goal", goals)
        self.assertNotIn("family", assistant)

    def test_ledger_feature_is_connected(self):
        backend = self.read("backend/app.py")
        dashboard = self.read("frontend/src/pages/Dashboard.jsx")
        ledger = self.read("frontend/src/pages/Ledger.jsx")
        self.assertIn("@app.get('/api/ledger')", backend)
        self.assertIn("Running balance = opening balance + credits - debits", backend)
        self.assertIn('import Ledger from"./Ledger"', dashboard)
        self.assertIn('"ledger","bi-journal-text","Ledger"', dashboard)
        self.assertIn("Ledger Algorithm", ledger)


if __name__ == "__main__":
    unittest.main()
