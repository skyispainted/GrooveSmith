#!/usr/bin/env python3
"""Convert a GM-channel-10 drum MIDI into proper drum-set MusicXML.

Percussion clef, unpitched notes at standard staff positions (percussion clef is
treated like treble clef per MusicXML spec), x-noteheads for cymbals/hi-hat.

Rhythm handling:
- tempo can be supplied (estimated from the drums stem upstream); else read from MIDI.
- the silent intro before the first drum hit is trimmed (bars start at the first hit,
  aligned to the beat grid).
- empty slots are merged into the largest possible rests instead of 16th-rest spam.
"""
import sys
import pretty_midi
from music21 import stream, note, percussion, clef, meter, duration, tempo, instrument, metadata
from music21.musicxml import m21ToXml

# GM percussion (MIDI note) -> (display step, octave, notehead) on a percussion(=treble) clef.
# Standard drum-set layout (matches common MuseScore/Guitar Pro convention).
DRUM_MAP = {
    35: ("F", 4, "normal"),   # Acoustic Bass Drum
    36: ("F", 4, "normal"),   # Bass Drum 1
    38: ("C", 5, "normal"),   # Acoustic Snare
    40: ("C", 5, "normal"),   # Electric Snare
    37: ("C", 5, "x"),        # Side Stick
    39: ("C", 5, "x"),        # Hand Clap
    41: ("F", 4, "normal"),   # Low Floor Tom
    43: ("A", 4, "normal"),   # High Floor Tom
    45: ("D", 5, "normal"),   # Low Tom
    47: ("E", 5, "normal"),   # Low-Mid Tom
    48: ("E", 5, "normal"),   # Hi-Mid Tom
    50: ("F", 5, "normal"),   # High Tom
    42: ("G", 5, "x"),        # Closed Hi-Hat
    44: ("D", 4, "x"),        # Pedal Hi-Hat (below staff)
    46: ("G", 5, "circle-x"), # Open Hi-Hat
    49: ("A", 5, "x"),        # Crash Cymbal 1
    57: ("A", 5, "x"),        # Crash Cymbal 2
    51: ("F", 5, "x"),        # Ride Cymbal 1
    59: ("F", 5, "x"),        # Ride Cymbal 2
    53: ("F", 5, "diamond"),  # Ride Bell
    55: ("B", 5, "x"),        # Splash Cymbal
    52: ("B", 5, "x"),        # China Cymbal
}
DEFAULT = ("C", 5, "normal")


def _make_unpitched(pitch, ql):
    step, octv, nh = DRUM_MAP.get(pitch, DEFAULT)
    u = note.Unpitched(displayName=f"{step}{octv}")
    u.duration = duration.Duration(ql)
    if nh in ("x", "circle-x", "diamond"):
        u.notehead = nh
    return u


def build_drum_score(midi_path, bpm=None, max_measures=200, title=None):
    pm = pretty_midi.PrettyMIDI(midi_path)
    if bpm is None:
        try:
            _, tempi = pm.get_tempo_changes()
            bpm = float(tempi[0]) if len(tempi) else 120.0
        except Exception:
            bpm = 120.0
    if not bpm or bpm <= 0:
        bpm = 120.0

    events = []
    for inst in pm.instruments:
        for n in inst.notes:
            events.append((float(n.start), int(n.pitch)))
    events.sort()
    if not events:
        events = []

    sec_per_beat = 60.0 / bpm
    grid = sec_per_beat / 4.0          # 16th-note grid
    slots_per_measure = 16             # 4/4, sixteenths

    # Keep the score aligned to absolute audio time (score time == MIDI time == audio
    # time) so the playback highlight matches the original. The silent intro before the
    # first hit becomes clean whole-measure rests (rest-merging below handles that),
    # NOT a time shift -- shifting would desync the highlight from the audio.
    origin = 0.0

    # bucket pitches by quantized 16th slot (relative to origin)
    slots = {}
    for start, pitch in events:
        q = int(round((start - origin) / grid))
        if q < 0:
            q = 0
        slots.setdefault(q, set()).add(pitch)

    max_slot = max(slots.keys()) if slots else 0
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

    QL = 0.25  # a 16th note

    for m_idx in range(total_measures):
        meas = stream.Measure(number=m_idx + 1)
        base = m_idx * slots_per_measure
        s = 0
        while s < slots_per_measure:
            slot = base + s
            hit = slots.get(slot)
            if hit:
                unps = [_make_unpitched(p, QL) for p in sorted(hit)]
                if len(unps) == 1:
                    meas.append(unps[0])
                else:
                    ch = percussion.PercussionChord(unps)
                    ch.duration = duration.Duration(QL)
                    meas.append(ch)
                s += 1
            else:
                # merge consecutive empty slots into one rest, but do not cross
                # beat boundaries messily: cap rest length to remaining slots and
                # to a run of empties.
                run = 0
                while s + run < slots_per_measure and not slots.get(base + s + run):
                    run += 1
                # split run into note-values that align to the grid (max whole=16 slots)
                start_s = s
                remaining = run
                pos = start_s
                while remaining > 0:
                    # largest power-of-two chunk that fits and aligns to pos
                    chunk = 1
                    for c in (16, 8, 4, 2, 1):
                        if c <= remaining and pos % c == 0:
                            chunk = c
                            break
                    meas.append(note.Rest(quarterLength=QL * chunk))
                    pos += chunk
                    remaining -= chunk
                s += run
        try:
            meas.makeBeams(inPlace=True)
        except Exception:
            pass
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
