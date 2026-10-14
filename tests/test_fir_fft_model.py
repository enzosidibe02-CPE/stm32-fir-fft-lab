import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fir_fft_model as m  # noqa: E402


@pytest.fixture(scope="module")
def r():
    return m.run()


def test_parameters_parsed_from_firmware(r):
    p = r["params"]
    assert (p["fft_length"], p["fs"], p["n_taps"], p["n_block"]) == (2048, 16384, 32, 32)
    assert len(p["taps"]) == 32


def test_taps_are_symmetric_so_filter_is_linear_phase(r):
    t = r["params"]["taps"]
    assert np.allclose(t, t[::-1], atol=1e-12)


def test_block_processing_equals_direct_convolution(r):
    ref = np.convolve(r["x"], r["params"]["taps"])[: len(r["x"])]
    assert np.allclose(r["y"], ref, atol=1e-9)


def test_test_tones_fall_on_exact_fft_bins(r):
    fs, n = r["params"]["fs"], r["params"]["fft_length"]
    assert 400 * n / fs == 50 and 3000 * n / fs == 375
    top2 = sorted(np.argsort(r["mag_in"])[-2:])
    assert top2 == [50, 375]
    assert r["mag_in"][50] == pytest.approx(n / 2, rel=1e-9)   # unit-amplitude cosine -> N/2


def test_in_band_tone_is_preserved(r):
    gain = r["mag_out"][50] / r["mag_in"][50]
    assert 0.95 < gain < 1.10


def test_out_of_band_tone_is_attenuated_by_at_least_40_db(r):
    att_db = 20 * np.log10(r["mag_out"][375] / r["mag_in"][375])
    assert att_db < -40


def test_response_matches_scipy_freqz(r):
    p = r["params"]
    w, h = signal.freqz(p["taps"], worN=[2 * np.pi * 400 / p["fs"], 2 * np.pi * 3000 / p["fs"]])
    assert abs(h[0]) == pytest.approx(r["mag_out"][50] / r["mag_in"][50], rel=0.01)
    assert abs(h[1]) == pytest.approx(r["mag_out"][375] / r["mag_in"][375], rel=0.20)
