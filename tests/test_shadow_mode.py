import pytest

from shadow_mode import build_report

pytestmark = [pytest.mark.unit]


def test_shadow_report_contains_header(tmp_path):
    # create a file with TODO
    f = tmp_path / "a.py"
    f.write_text("# TODO: test\nprint('x')")

    report = build_report([str(tmp_path)])
    assert "Shadow Mode" in report
    assert "TODO" in report
