#!/usr/bin/env python3
"""Convert a GM-channel-10 drum MIDI into proper drum-set MusicXML
(percussion clef, unpitched notes at standard staff positions, x-noteheads for cymbals/hi-hat).

Standard drum-set notation layout (5-line staff, percussion clef).
We place notes by (display-step, display-octave) matching the common convention, and
choose notehead shape per instrument (x / circle-x / normal / diamond).
"""
import sys
import pretty_midi
from music21 import stream, note, percussion, clef, meter, duration, tempo, layout, instrument
from music21.musicxml import m21ToXml

# GM percussion (MIDI note) -> (display pitch on staff, notehead, name)
# display pitch uses standard treble/perc-clef positions used by MuseScore drumset.
# Format: midi_pitch: (step, octave, notehead)
# notehead: "x" (cymbals/hihat), "circle-x" (open hh), "normal" (drums), "diamond" (ride bell / cymbal choke opt)
DRUM_MAP = {
    35: ("F", 4, "normal"),   # Acoustic Bass Drum
    36: ("F", 4, "normal"),   # Bass Drum 1  (bottom space, F4 in treble->perc)
    38: ("C", 5, "normal"),   # Acoustic Snare (3rd space)
    40: ("C", 5, "normal"),   # Electric Snare
    37: ("C", 5, "x"),        # Side Stick -> snare line, x
    39: ("C", 5, "x"),        # Hand Clap
    41: ("A", 4, "normal"),   # Low Floor Tom
    43: ("A", 4, "normal"),   # High Floor Tom
    45: ("D", 5, "normal"),   # Low Tom
    47: ("E", 5, "normal"),   # Low-Mid Tom
    48: ("E", 5, "normal"),   # Hi-Mid Tom
    50: ("F", 5, "normal"),   # High Tom
    42: ("G", 5, "x"),        # Closed Hi-Hat (top, x)
    44: ("D", 4, "x"),        # Pedal Hi-Hat (below staff, x)
    46: ("G", 5, "circle-x"), # Open Hi-Hat (x with circle)
    49: ("A", 5, "x"),        # Crash Cymbal 1 (above top line, x)
    57: ("A", 5, "x"),        # Crash Cymbal 2
    51: ("F", 5, "x"),        # Ride Cymbal 1
    59: ("F", 5, "x"),        # Ride Cymbal 2
    53: ("F", 5, "diamond"),  # Ride Bell
    55: ("B", 5, "x"),        # Splash Cymbal
    52: ("B", 5, "x"),        # China Cymbal
}
DEFAULT = ("C", 5, "normal")


def build_drum_score(midi_path, bpm_default=120):
    pm = pretty_midi.PrettyMIDI(midi_path)
    # tempo
    try:
        _, tempi = pm.get_tempo_changes()
        bpm = float(tempi[0]) if len(tempi) else bpm_default
    except Exception:
        bpm = bpm_default

    # collect drum note onsets (seconds) from any is_drum instrument
    events = []
    for inst in pm.instruments:
        if inst.is_drum or True:  # ADTOF marks is_drum; accept all to be safe
            for n in inst.notes:
                events.append((n.start, n.pitch, n.velocity))
    events.sort()

    sec_per_beat = 60.0 / bpm
    # quantize onsets to 16th grid
    grid = sec_per_beat / 4.0

    sc = stream.Score()
    from music21 import metadata
    sc.insert(0, metadata.Metadata())
    sc.metadata.title = "Drum Score"
    sc.metadata.composer = ""
    part = stream.Part()
    perc = instrument.Percussion()
    perc.instrumentName = "Drum Set"
    perc.instrumentAbbreviation = "D. S."
    part.insert(0, perc)
    part.insert(0, clef.PercussionClef())
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark(number=round(bpm)))

    # group events by quantized 16th slot; make each a percussion note (or chord)
    from collections import defaultdict
    slots = defaultdict(list)
    for start, pitch, vel in events:
        q = round(start / grid)
        slots[q].append(pitch)

    if not slots:
        maxslot = 0
    else:
        maxslot = max(slots.keys())

    beats_per_measure = 4
    slots_per_measure = beats_per_measure * 4  # 16th notes

    total_measures = maxslot // slots_per_measure + 1
    ql_per_slot = 0.25  # 16th note = 0.25 quarterLength

    for m_idx in range(total_measures):
        meas = stream.Measure(number=m_idx + 1)
        for s in range(slots_per_measure):
            slot = m_idx * slots_per_measure + s
            pitches = slots.get(slot, [])
            off = s * ql_per_slot
            if not pitches:
                r = note.Rest(quarterLength=ql_per_slot)
                meas.insert(off, r)
            else:
                unps = []
                for p in sorted(set(pitches)):
                    step, octv, nh = DRUM_MAP.get(p, DEFAULT)
                    u = note.Unpitched(displayName=f"{step}{octv}")
                    u.duration = duration.Duration(ql_per_slot)
                    if nh == "x":
                        u.notehead = "x"
                    elif nh == "circle-x":
                        u.notehead = "circle-x"
                    elif nh == "diamond":
                        u.notehead = "diamond"
                    unps.append(u)
                if len(unps) == 1:
                    meas.insert(off, unps[0])
                else:
                    ch = percussion.PercussionChord(unps)
                    ch.duration = duration.Duration(ql_per_slot)
                    meas.insert(off, ch)
        meas.makeBeams(inPlace=True)
        part.append(meas)

    sc.insert(0, part)
    return sc


def main():
    midi_path = sys.argv[1]
    out_xml = sys.argv[2]
    sc = build_drum_score(midi_path)
    exporter = m21ToXml.GeneralObjectExporter(sc)
    data = exporter.parse()
    with open(out_xml, "wb") as fh:
        fh.write(data)
    print("WROTE", out_xml)


if __name__ == "__main__":
    main()
