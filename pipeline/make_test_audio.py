import numpy as np, soundfile as sf, sys
SR = 44100
bpm = 100
beat = 60.0 / bpm
bars = 4
total = beat * 4 * bars
n = int(total * SR)
audio = np.zeros(n, dtype=np.float32)
def env(length, decay):
    return np.exp(-np.linspace(0, decay, length)).astype(np.float32)
def place(sig, at):
    i = int(at * SR)
    j = min(i + len(sig), n)
    audio[i:j] += sig[: j - i]
def kick():
    L = int(0.18 * SR)
    tt = np.arange(L) / SR
    f = 120 * np.exp(-tt * 30) + 45
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env(L, 6) * 0.9).astype(np.float32)
def snare():
    L = int(0.15 * SR)
    noise = np.random.randn(L).astype(np.float32)
    tone = np.sin(2 * np.pi * 190 * np.arange(L) / SR).astype(np.float32)
    return ((0.7 * noise + 0.3 * tone) * env(L, 12) * 0.7).astype(np.float32)
def hat():
    L = int(0.05 * SR)
    noise = np.random.randn(L).astype(np.float32)
    hp = np.diff(noise, prepend=noise[0])
    return (hp * env(L, 20) * 0.35).astype(np.float32)
for bar in range(bars):
    b0 = bar * 4 * beat
    place(kick(), b0 + 0 * beat)
    place(kick(), b0 + 2 * beat)
    place(snare(), b0 + 1 * beat)
    place(snare(), b0 + 3 * beat)
    for e in range(8):
        place(hat(), b0 + e * (beat / 2))
bass_freqs = [55, 55, 73.42, 65.41]
for bar in range(bars):
    fr = bass_freqs[bar % len(bass_freqs)]
    a = int(bar * 4 * beat * SR)
    b = int((bar + 1) * 4 * beat * SR)
    seg = np.arange(b - a) / SR
    audio[a:b] += (0.25 * np.sin(2 * np.pi * fr * seg)).astype(np.float32)
audio = audio / (np.max(np.abs(audio)) + 1e-6) * 0.9
sf.write(sys.argv[1], audio, SR)
print(WROTE, sys.argv[1], dur, total, SR, SR)
