#!/usr/bin/env python3
"""Convert a GM-channel-10 drum MIDI into proper drum-set MusicXML.

Standard jazz/rock drum notation:
- percussion clef (treated like treble clef for display-step/octave per MusicXML spec)
- TWO voices for hand/foot separation:
    Voice 1 (hands): snare, all toms, hi-hat, crash, ride  -> stems UP  (beams on top)
    Voice 2 (feet):  bass drum, pedal hi-hat                -> stems DOWN (beams below)
  music21 emits <backup>/<voice>/<stem> automatically from two Voice streams.
- x noteheads for cymbals/hi-hat, circle-x for open hi-hat, diamond for ride bell,
  normal (filled) heads for drums.
Rhythm: quantized to a 16th grid at the given/estimated tempo; empty slots merged
into the largest aligned rests. Score time == MIDI time == audio time (no intro trim).
"""
import sys
import pretty_midi
from music21 import stream, note, percussion, clef, meter, duration, tempo, instrument, metadata
from music21.musicxml import m21ToXml

# GM percussion (MIDI note) -> (display step, octave, notehead) on a percussion(=treble) clef.
DRUM_MAP = {
    # ---- feet (Voice 2, stems down) ----
    35: ("F", 4, "normal"),   # Acoustic Bass Drum
    36: ("F", 4, "normal"),   # Bass Drum 1
    44: ("D", 4, "x"),        # Pedal Hi-Hat (below staff)
    # ---- hands: snare (Voice 1, stems up) ----
    38: ("C", 5, "normal"),   # Acoustic Snare (3rd space)
    40: ("C", 5, "normal"),   # Electric Snare
    37: ("C", 5, "x"),        # Side Stick -> snare line, x head
    39: ("C", 5, "x"),        # Hand Clap
    # ---- toms (Voice 1): high -> E5, mid -> D5, low -> B4 ----
    50: ("E", 5, "normal"),   # High Tom
    48: ("D", 5, "normal"),   # Hi-Mid Tom
    47: ("D", 5, "normal"),   # Low-Mid Tom
    45: ("B", 4, "normal"),   # Low Tom
    43: ("B", 4, "normal"),   # High Floor Tom
    41: ("A", 4, "normal"),   # Low Floor Tom
    # ---- cymbals / hi-hat (Voice 1) ----
    42: ("G", 5, "x"),        # Closed Hi-Hat  (top)
    46: ("G", 5, "circle-x"), # Open Hi-Hat
    49: ("A", 5, "x"),        # Crash Cymbal 1 (above top line)
    57: ("A", 5, "x"),        # Crash Cymbal 2
    55: ("A", 5, "x"),        # Splash Cymbal
    52: ("A", 5, "x"),        # China Cymbal
    51: ("F", 5, "x"),        # Ride Cymbal 1
    59: ("F", 5, "x"),        # Ride Cymbal 2
    53: ("F", 5, "diamond"),  # Ride Bell
}
DEFAULT = ("C", 5, "normal")

# feet go to Voice 2 (stems down); everything else to Voice 1 (stems up)
FEET = {35, 36, 44}

# --- difficulty presets ---
# grid: quantize resolution (subdivisions per beat). 4=16th, 2=8th.
# keep: which GM pitches to keep (None = keep all).
# collapse: remap toms/extra cymbals down to core pieces for the simplest chart.
CORE_KICK = {35, 36}
CORE_SNARE = {38, 40, 37, 39}
CORE_HAT = {42, 46, 44}
CORE = CORE_KICK | CORE_SNARE | CORE_HAT
# a "standard" set adds ride + crash but drops most toms/aux cymbals
STANDARD_EXTRA = {49, 57, 51, 59, 53, 50, 48, 47, 45}

DIFFICULTY = {
    "simple":   {"grid": 2, "keep": CORE,                  "collapse": True},   # 8th grid, kick/snare/hat only
    "standard": {"grid": 4, "keep": CORE | STANDARD_EXTRA, "collapse": False},  # 16th, + ride/crash/toms
    "full":     {"grid": 4, "keep": None,                  "collapse": False},  # everything
}

# collapse map for simple mode: any tom -> a single mid tom voice-1 note; splash/china -> crash
COLLAPSE = {41: 45, 43: 45, 47: 45, 48: 45, 50: 45, 45: 45,
            55: 49, 52: 49, 57: 49, 59: 51}


def _make_unpitched(pitch, ql, stem):
    step, octv, nh = DRUM_MAP.get(pitch, DEFAULT)
    u = note.Unpitched(displayName=f"{step}{octv}")
    u.duration = duration.Duration(ql)
    if nh in ("x", "circle-x", "diamond"):
        u.notehead = nh
    u.stemDirection = stem
    return u


def _fill_voice(slots_for_voice, base, slots_per_measure, QL, stem):
    """Build one Voice stream spanning the whole measure: notes where this voice
    plays, merged rests elsewhere. slots_for_voice: {slot_index_within_measure: [pitches]}"""
    v = stream.Voice()
    s = 0
    while s < slots_per_measure:
        pitches = slots_for_voice.get(s)
        if pitches:
            unps = [_make_unpitched(p, QL, stem) for p in sorted(set(pitches))]
            if len(unps) == 1:
                el = unps[0]
            else:
                el = percussion.PercussionChord(unps)
                el.duration = duration.Duration(QL)
                el.stemDirection = stem
            v.append(el)
            s += 1
        else:
            run = 0
            while s + run < slots_per_measure and not slots_for_voice.get(s + run):
                run += 1
            pos = s
            remaining = run
            while remaining > 0:
                chunk = 1
                for c in (16, 8, 4, 2, 1):
                    if c <= remaining and pos % c == 0:
                        chunk = c
                        break
                v.append(note.Rest(quarterLength=QL * chunk))
                pos += chunk
                remaining -= chunk
            s += run
    try:
        v.makeBeams(inPlace=True)
    except Exception:
        pass
    return v


def build_drum_score(midi_path, bpm=None, max_measures=200, title=None, difficulty="standard"):
    pm = pretty_midi.PrettyMIDI(midi_path)
    if bpm is None:
        try:
            _, tempi = pm.get_tempo_changes()
            bpm = float(tempi[0]) if len(tempi) else 120.0
        except Exception:
            bpm = 120.0
    if not bpm or bpm <= 0:
        bpm = 120.0

    preset = DIFFICULTY.get(difficulty, DIFFICULTY["standard"])
    subdiv = preset["grid"]          # subdivisions per beat (4=16th, 2=8th)
    keep = preset["keep"]            # set of pitches to keep, or None for all
    collapse = preset["collapse"]

    events = []
    for inst in pm.instruments:
        for n in inst.notes:
            p = int(n.pitch)
            if collapse and p in COLLAPSE:
                p = COLLAPSE[p]
            if keep is not None and p not in keep:
                continue
            events.append((float(n.start), p))
    events.sort()

    sec_per_beat = 60.0 / bpm
    grid = sec_per_beat / subdiv                 # seconds per grid step
    slots_per_measure = 4 * subdiv               # 4/4
    QL = 1.0 / subdiv                            # quarterLength of one grid step

    # split into hand (voice1) / foot (voice2) buckets, keyed by absolute 16th slot
    hands = {}
    feet = {}
    for start, pitch in events:
        q = int(round(start / grid))
        if q < 0:
            q = 0
        (feet if pitch in FEET else hands).setdefault(q, []).append(pitch)

    all_slots = list(hands.keys()) + list(feet.keys())
    max_slot = max(all_slots) if all_slots else 0
    total_measures = min(max_measures, max_slot // slots_per_measure + 1)

    sc = stream.Score()
    sc.insert(0, metadata.Metadata())
    sc.metadata.title = title if title else "Drum Score"
    part = stream.Part()
    perc = instrument.Percussion()
    perc.instrumentName = "Drum Set"
    perc.instrumentAbbreviation = "D.S."
    part.insert(0, perc)
    part.insert(0, clef.PercussionClef())
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark(number=round(bpm)))

    for m_idx in range(total_measures):
        meas = stream.Measure(number=m_idx + 1)
        base = m_idx * slots_per_measure
        # slice this measure's slots for each voice (relative index 0..15)
        h_local = {}
        f_local = {}
        for s in range(slots_per_measure):
            slot = base + s
            if slot in hands:
                h_local[s] = hands[slot]
            if slot in feet:
                f_local[s] = feet[slot]
        v1 = _fill_voice(h_local, base, slots_per_measure, QL, "up")
        v1.id = "1"
        v2 = _fill_voice(f_local, base, slots_per_measure, QL, "down")
        v2.id = "2"
        meas.insert(0, v1)
        meas.insert(0, v2)
        part.append(meas)

    sc.insert(0, part)
    return sc


def main():
    midi_path = sys.argv[1]
    out_xml = sys.argv[2]
    bpm = float(sys.argv[3]) if len(sys.argv) > 3 else None
    sc = build_drum_score(midi_path, bpm=bpm)
    data = m21ToXml.GeneralObjectExporter(sc).parse()
    with open(out_xml, "wb") as fh:
        fh.write(data)
    print("WROTE", out_xml)


if __name__ == "__main__":
    main()
