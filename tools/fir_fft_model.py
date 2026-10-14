"""Host-side reproduction of the Lab 8 firmware computation.

Parses the FIR coefficients and sampling parameters directly from
firmware/Core/Src/main.c, rebuilds the same test signal (400 Hz + 3 kHz cosines),
applies the FIR in 32-sample blocks exactly as the firmware does, and computes
the same 2048-point FFT magnitudes. Nothing here is hardware data.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

MAIN_C = Path(__file__).resolve().parents[1] / "firmware/Core/Src/main.c"


def _define(src: str, name: str) -> int:
    m = re.search(rf"#define\s+{name}\s+(\d+)", src)
    if not m:
        raise ValueError(f"#define {name} not found in {MAIN_C}")
    return int(m.group(1))


def load_firmware_params(path: Path = MAIN_C) -> dict:
    src = path.read_text()
    body = src[src.index("Coeffs[N_TAPS]"):]
    body = body[body.index("{") + 1 : body.index("}")]
    taps = np.array([float(v) for v in re.findall(r"-?\d+\.\d+(?:e-?\d+)?", body)])
    params = dict(
        fft_length=_define(src, "FFT_LENGTH"),
        fs=_define(src, "SAMPLING_RATE"),
        n_taps=_define(src, "N_TAPS"),
        n_block=_define(src, "N_BLOCK"),
        taps=taps,
    )
    if len(taps) != params["n_taps"]:
        raise ValueError(f"expected {params['n_taps']} taps, parsed {len(taps)}")
    return params


def test_signal(n: int, fs: float, f_low: float = 400.0, f_high: float = 3000.0) -> np.ndarray:
    k = np.arange(n)
    return np.cos(2 * np.pi * f_low * k / fs) + np.cos(2 * np.pi * f_high * k / fs)


def fir_blocks(x: np.ndarray, taps: np.ndarray, n_block: int) -> np.ndarray:
    """Block-wise FIR with persistent state, as arm_fir_f32 is called in main()."""
    n_taps = len(taps)
    state = np.zeros(n_taps - 1)
    out = np.empty_like(x)
    for i in range(0, len(x), n_block):
        blk = x[i : i + n_block]
        ext = np.concatenate([state, blk])
        for j in range(len(blk)):
            out[i + j] = np.dot(taps[::-1], ext[j : j + n_taps])
        state = ext[-(n_taps - 1) :]
    return out


def magnitude_spectrum(x: np.ndarray) -> np.ndarray:
    """Unnormalised |FFT|, first N/2 bins, like arm_cmplx_mag_f32 on arm_rfft_fast_f32."""
    return np.abs(np.fft.rfft(x))[: len(x) // 2]


def run() -> dict:
    p = load_firmware_params()
    n, fs = p["fft_length"], p["fs"]
    x = test_signal(n, fs)
    y = fir_blocks(x, p["taps"], p["n_block"])
    return dict(params=p, x=x, y=y, mag_in=magnitude_spectrum(x), mag_out=magnitude_spectrum(y),
                freq=np.arange(n // 2) * fs / n)
