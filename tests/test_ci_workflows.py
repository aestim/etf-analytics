"""CI workflows preserve the repository/warehouse ownership boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scheduled_ingest_never_writes_to_main():
    workflow = (ROOT / ".github" / "workflows" / "daily_ingest.yml").read_text(
        encoding="utf-8"
    )

    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "${{ runner.temp }}/etf-raw" in workflow
    assert "POSTGRES_HOST and POSTGRES_PASSWORD are required" in workflow

    for forbidden in ("contents: write", "git add", "git commit", "git push"):
        assert forbidden not in workflow
