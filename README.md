# Successive Interference Cancellation (SIC) — BPSK Co-Channel Signal Extraction

> **tl;dr:** Two BPSK emitters share the exact same carrier frequency. The stronger one is 15 dB louder. This repo shows how to mathematically reconstruct and subtract the dominant signal from the raw IQ recording, exposing the hidden weaker emitter underneath.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Data via LFS](https://img.shields.io/badge/data-Git%20LFS-orange)
![Topics](https://img.shields.io/badge/topics-SIC%20%7C%20BPSK%20%7C%20DSP%20%7C%20SDR-purple)

---

## 1. The Engineering Problem

A monitoring post records 2 seconds of a 200 kHz band centred on 433.05 MHz. Signals analysis confirms **two simultaneous BPSK emitters on the exact same carrier frequency** — not adjacent channels, not slightly offset — the same frequency. The stronger emitter is 15 dB louder and runs at 12.5 kBd. The weaker emitter's baud rate is unknown.

A standard BPSK demodulator will happily decode the loud signal and present it as a clean, correct output — making the operator believe the job is done. The mission-critical traffic is in the other signal.

---

## 2. Why Naive Demodulators Fail

A BPSK demodulator finds the strongest phase component and locks to it. With a 15 dB power difference, the loud signal dominates the phase tracking loop completely. The quiet signal contributes only noise-level perturbations to the loop discriminant — it is invisible to any standard receiver.

Even switching to a blind source separation algorithm (ICA) fails without prior information, because both signals share the same carrier and the power ratio is too extreme.

---

## 3. The Mathematical Foundation

### 3.1 BPSK Signal Model

A BPSK signal is:

```
s(t) = A · b(t) · cos(2πf_c·t + φ)
```

where `b(t) ∈ {-1, +1}` is the bit stream, `A` is amplitude, `f_c` is carrier, `φ` is carrier phase.

In complex baseband (IQ representation):

```
s_IQ(t) = A · b(t) · e^(j·φ)
```

Two co-channel signals produce:
```
r(t) = s_loud(t) + s_quiet(t) + n(t)
```

### 3.2 Costas Loop Phase Tracking

A Costas Loop is a phase-locked loop (PLL) adapted for suppressed-carrier modulations like BPSK. Its phase discriminator is:

```
e(t) = Im[r(t) · conj(v(t))] · Re[r(t) · conj(v(t))]
```

where `v(t)` is the local VCO output. The loop drives `e(t) → 0`, converging to the carrier phase of the dominant signal.

### 3.3 Gardner Timing Error Detector

For symbol timing recovery, the Gardner TED computes:

```
τ_error = Re[ x(nT - T/2) · (conj(x(nT)) - conj(x(nT - T))) ]
```

where `T` is the symbol period. This is data-aided and works without a pilot tone.

### 3.4 The SIC Subtraction

Once the loud signal is decoded:
1. Map recovered bits to BPSK symbols: `sym = 2·bit - 1` → `{-1, +1}`
2. Pulse-shape with a rectangular filter at the estimated baud rate
3. Apply the recovered frequency offset and phase: `reconstructed = sym · A_loud · e^(j·(2π·Δf·t + φ_loud))`
4. Subtract:

```
clean_IQ = raw_IQ - reconstructed_loud_IQ
```

The noise floor drops by ~15 dB, exposing the quiet signal.

### 3.5 Weak Signal Baud Rate Estimation

Square the residual IQ to remove BPSK modulation:

```
|clean_IQ(t)|² → FFT → peak at 2 × baud_rate
```

The FFT peak gives the unknown baud rate directly.

---

## 4. Algorithmic Breakdown

1. **Load IQ**: Read `cf32_le` SigMF file → complex64 array
2. **Loud Demodulation**: Costas loop → Gardner TED → hard decisions at 12.5 kBd → bits + recovered (Δf, φ, A)
3. **Waveform Reconstruction**: Bits → symbols → rectangular pulse-shape → frequency/phase shift → scale
4. **Subtraction**: `clean_IQ = raw_IQ - reconstructed`
5. **Baud Rate Estimation**: FFT of `|clean_IQ|²` → find peak at `2 × baud_rate`
6. **Weak Demodulation**: Costas loop on `clean_IQ` at discovered baud rate
7. **Sync Word Search**: Scan for `0x7E1D` = `0111111000011101` to frame the bit stream
8. **ASCII Decode**: Extract 8-bit ASCII after sync word

---

## 5. Dataset — SigMF Schema

| File | Size | Format | Description |
|------|------|--------|-------------|
| `data/cochannel.sigmf-data` | 3.2 MB | `cf32_le` | Raw IQ, 200 kHz SR, 400k samples |
| `data/cochannel.sigmf-meta` | 357 B | JSON | Sample rate 200000, centre 433.05 MHz |

```python
import numpy as np
raw = np.fromfile("data/cochannel.sigmf-data", dtype=np.float32)
iq  = raw[0::2] + 1j * raw[1::2]   # interleaved cf32_le → complex64
```

---

## 6. Repository Structure

```
successive-interference-cancellation/
├── .gitattributes      # Git LFS filter for *.sigmf-data
├── .gitignore
├── LICENSE             # MIT
├── README.md
├── requirements.txt
├── data/
│   ├── cochannel.sigmf-data    ← Git LFS (3.2 MB)
│   └── cochannel.sigmf-meta
└── solve.py            # Full SIC pipeline
```

---

## 7. Setup and Execution

```bash
git clone https://github.com/<username>/successive-interference-cancellation.git
cd successive-interference-cancellation
git lfs pull

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python solve.py
```

---

## 8. Further Reading

- Proakis & Salehi — *Digital Communications*, 5th Ed. Ch. 6 (Carrier and timing recovery)
- Viterbi, A.J. — "Nonlinear estimation of PSK-modulated carrier phase", *IEEE Trans. IT*, 1983
- GNU Radio — [gnuradio.org](https://www.gnuradio.org) (Costas loop and timing recovery blocks)
- Rice, M. — *Digital Communications: A Discrete-Time Approach*, Ch. 8 (Gardner TED)
