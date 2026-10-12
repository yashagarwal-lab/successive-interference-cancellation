import numpy as np

raw = np.fromfile("cochannel.sigmf-data", dtype=np.float32)
x = raw[0::2] + 1j*raw[1::2]

phase = np.angle(np.mean(x**2)) / 2.0
x_rot = x * np.exp(-1j * phase)

# Extract strong signal (12.5 kBd -> 16 sps)
t0 = 5
num_symbols = (len(x) - t0) // 16
amps = []
syms = []
for n in range(num_symbols):
    w = x_rot[t0 + n*16 : t0 + n*16 + 16]
    mean_val = np.mean(w.real)
    sym = np.sign(mean_val)
    syms.append(sym)
    amps.append(mean_val * sym)
A_global = np.mean(amps)

strong = np.zeros_like(x_rot, dtype=np.complex128)
for n in range(num_symbols):
    strong[t0 + n*16 : t0 + n*16 + 16] = syms[n] * A_global
strong[0:t0] = np.sign(np.mean(x_rot[0:t0].real)) * A_global
w_next = x_rot[t0 + num_symbols*16:]
if len(w_next) > 0:
    strong[t0 + num_symbols*16:] = np.sign(np.mean(w_next.real)) * A_global

# Subtract
x_weak = x_rot - strong

# Demodulate weak signal (assume 8 kBd -> 25 sps)
sps = 25
mf = np.ones(sps)/sps
filt = np.convolve(x_weak.real, mf, mode='valid')

# Find best offset for 8 kBd
energies = [np.sum(np.abs(filt[off::sps])**2) for off in range(sps)]
best_off = np.argmax(energies)
print(f"Weak signal best offset (8 kBd): {best_off}")

sampled = filt[best_off::sps]
bits = (sampled > 0).astype(int)

# sync word
sync = "0111111000011101"
sync_bits = np.array([int(b) for b in sync])

# We don't know the exact starting index or polarity
for polarity in [1, -1]:
    if polarity == -1:
        cur_bits = 1 - bits
    else:
        cur_bits = bits
    
    # search for sync
    for i in range(len(cur_bits) - 16):
        if np.array_equal(cur_bits[i:i+16], sync_bits):
            # found sync! Decode next bytes
            msg = []
            for j in range(i+16, len(cur_bits)-8, 8):
                byte_bits = cur_bits[j:j+8]
                byte_val = int("".join(map(str, byte_bits)), 2)
                # alternative: LSB first? Let's assume MSB first, if not try LSB
                msg.append(chr(byte_val))
            msg_str = "".join(msg)
            if "RFCTF" in msg_str:
                print(f"FOUND FLAG! Polarity {polarity}")
                print(msg_str)
                break
    else:
        continue
    break

