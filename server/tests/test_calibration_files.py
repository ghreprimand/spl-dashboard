"""Broadened calibration-file import.

Fixtures are synthetic but shaped like the vendor exports named in each case.
The parser reads frequency-response points from all of them and only reports a
sensitivity (Sens Factor) when the file actually contains one. It never invents
an absolute sensitivity that is not present.
"""

from pathlib import Path

import numpy as np
import pytest

from spl_dashboard.calibration import parse_calibration
from spl_dashboard.dsp import SAMPLE_RATE

FIXTURES = Path(__file__).parent / "fixtures" / "calibration"


def load(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_minidsp_umik2_provides_sensitivity_and_serial():
    cal = parse_calibration(load("umik2_synthetic.txt"))
    assert cal is not None
    assert cal.sensitivity == pytest.approx(-1.50)
    assert cal.serial == "8000123"
    assert len(cal.frequencies) == 6
    # A usable correction FIR can be built from the response.
    assert cal.fir(SAMPLE_RATE).shape == (2049,)


@pytest.mark.parametrize(
    ("name", "points"),
    [
        ("dayton_umm6_synthetic.txt", 5),
        ("dayton_imm6_synthetic.txt", 3),
        ("dayton_emm6_synthetic.txt", 3),
        ("rew_export.cal", 4),
        ("earthworks_synthetic.txt", 3),
    ],
)
def test_response_only_files_parse_without_a_guessed_sensitivity(name, points):
    cal = parse_calibration(load(name))
    assert cal is not None
    # No Sens Factor in these files: absolute SPL must come from reference/manual.
    assert cal.sensitivity is None
    assert len(cal.frequencies) == points
    assert np.all(np.diff(cal.frequencies) > 0)
    assert cal.fir(SAMPLE_RATE).shape == (2049,)


def test_rew_three_column_ignores_phase_column():
    cal = parse_calibration(load("rew_export.cal"))
    assert cal is not None
    # The middle column (SPL/response) is used; the phase column is ignored.
    assert cal.response[1] == pytest.approx(0.0)
    assert cal.response[2] == pytest.approx(0.6)


def test_still_rejects_a_malformed_sensitivity_header():
    # A file that clearly declares a Sens Factor but mangles it must not be
    # silently accepted, and must not be treated as "no sensitivity".
    with pytest.raises(ValueError):
        parse_calibration('"Sens Factor = garbage"\n20 0\n1000 0\n')
