"""Regenerate results/ from the host-side reproduction. Run: python tools/make_figures.py"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

import fir_fft_model as m

OUT = Path(__file__).resolve().parents[1] / "results"
OUT.mkdir(exist_ok=True)
NAVY, BLUE, ORANGE = "#14213d", "#3a6ea5", "#c77d3a"


def style(ax):
    ax.grid(alpha=0.25)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def main():
    r = m.run()
    p = r["params"]
    fs, n = p["fs"], p["fft_length"]

    # --- filter response ---
    w, h = signal.freqz(p["taps"], worN=4096, fs=fs)
    mag_db = 20 * np.log10(np.maximum(np.abs(h), 1e-12))
    f3db = float(w[np.argmax(mag_db < mag_db[0] - 3)])
    stop_start = 3000.0 - 500.0
    gd = (len(p["taps"]) - 1) / 2

    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(w, mag_db, color=NAVY)
    for f, lab, c in ((400, "400 Hz tone", BLUE), (3000, "3 kHz tone", ORANGE)):
        ax.axvline(f, color=c, ls="--", lw=1)
        ax.annotate(lab, (f, -5), rotation=90, va="top", ha="right", color=c, fontsize=8)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    ax.set_title(f"32-tap FIR magnitude response (Fs = {fs} Hz)")
    ax.set_ylim(-80, 5)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "fir_response.png", dpi=150)
    plt.close(fig)

    # --- time and spectra ---
    fig, axes = plt.subplots(2, 2, figsize=(11, 6))
    t = np.arange(256) / fs * 1000
    axes[0, 0].plot(t, r["x"][:256], color=NAVY, lw=1, label="input")
    axes[0, 0].plot(t, r["y"][:256], color=ORANGE, lw=1.2, label="filtered")
    axes[0, 0].set_xlabel("Time (ms)")
    axes[0, 0].set_ylabel("Amplitude")
    axes[0, 0].set_title("First 256 samples")
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[0, 1].plot(r["freq"], r["mag_in"], color=NAVY, lw=1, label="input")
    axes[0, 1].plot(r["freq"], r["mag_out"], color=ORANGE, lw=1, label="filtered")
    axes[0, 1].set_xlabel("Frequency (Hz)")
    axes[0, 1].set_ylabel("|X[k]| (linear)")
    axes[0, 1].set_title("2048-pt FFT magnitude")
    axes[0, 1].legend(frameon=False, fontsize=8)
    db_in = 20 * np.log10(np.maximum(r["mag_in"], 1e-3))
    db_out = 20 * np.log10(np.maximum(r["mag_out"], 1e-3))
    axes[1, 0].plot(r["freq"], db_in, color=NAVY, lw=1)
    axes[1, 0].plot(r["freq"], db_out, color=ORANGE, lw=1)
    axes[1, 0].set_xlabel("Frequency (Hz)")
    axes[1, 0].set_ylabel("dB")
    axes[1, 0].set_title("Same spectra, dB scale")
    axes[1, 0].set_ylim(-40, 70)
    axes[1, 1].stem(np.arange(len(p["taps"])), p["taps"], linefmt=NAVY, markerfmt="o", basefmt=" ")
    axes[1, 1].set_xlabel("Tap index")
    axes[1, 1].set_ylabel("Coefficient")
    axes[1, 1].set_title("FIR coefficients (symmetric -> linear phase)")
    for a in axes.ravel():
        style(a)
    fig.suptitle("Reproduction of the Lab 8 firmware computation (no hardware data)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "signal_and_spectra.png", dpi=150)
    plt.close(fig)

    k400, k3k = 50, 375
    summary = dict(
        fs_hz=fs, fft_length=n, n_taps=p["n_taps"], bin_hz=fs / n,
        dc_gain=float(np.sum(p["taps"])),
        gain_400hz=float(r["mag_out"][k400] / r["mag_in"][k400]),
        atten_3khz_db=float(20 * np.log10(r["mag_out"][k3k] / r["mag_in"][k3k])),
        minus3db_hz=f3db,
        worst_attenuation_above_2500hz_db=float(mag_db[w >= stop_start].max()),
        group_delay_samples=gd, group_delay_ms=gd / fs * 1000,
        note="Host reproduction of firmware computation; not hardware measurements.",
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
