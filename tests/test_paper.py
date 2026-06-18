"""Phase 6 — paper and narrative artifact checks."""

import shutil
import subprocess
from pathlib import Path

PAPER_DIR = Path(__file__).resolve().parents[1] / "docs" / "paper"
PAPER_TEX = PAPER_DIR / "paper.tex"


class TestPaperArtifacts:
    def test_paper_tex_has_epistemic_ablation(self):
        text = PAPER_TEX.read_text(encoding="utf-8")
        assert "Epistemic Ablation Study" in text
        assert "0.750" in text
        assert "0.462" in text
        assert "tab:epistemic-ablation" in text

    def test_paper_title_updated(self):
        text = PAPER_TEX.read_text(encoding="utf-8")
        assert "Experience" in text
        assert "Knowledge" in text

    def test_submit_checklist_exists(self):
        assert (PAPER_DIR / "SUBMIT.md").exists()

    def test_changelog_v020(self):
        cl = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## v0.2.0" in cl
        assert "Epistemic Benchmark" in cl

    def test_readme_narrative(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        assert "可验证" in readme
        assert "epistemic_results" in readme or "IMPROVEMENT_PLAN" in readme

    def test_pdf_compiles_if_pdflatex_available(self):
        if not shutil.which("pdflatex"):
            return  # skip when TeX not installed
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "paper.tex"],
            cwd=PAPER_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stdout[-500:] + proc.stderr[-500:]
        assert (PAPER_DIR / "paper.pdf").exists()
