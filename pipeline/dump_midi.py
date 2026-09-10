import pretty_midi, sys, collections
p = sys.argv[1]
pm = pretty_midi.PrettyMIDI(p)
print("=== MIDI:", p, "===")
try:
    times, tempi = pm.get_tempo_changes()
    print("tempo_changes times", list(times)[:5], "bpm", list(tempi)[:5])
except Exception as e:
    print("tempo err", e)
print("end_time", round(pm.get_end_time(), 3))
print("n_instruments", len(pm.instruments))
GM = {35:"AcBass",36:"Bass1",37:"SideStick",38:"AcSnare",40:"ElSnare",41:"LFloorTom",
      42:"ClosedHH",43:"HFloorTom",44:"PedalHH",45:"LowTom",46:"OpenHH",47:"LoMidTom",
      48:"HiMidTom",49:"Crash1",50:"HighTom",51:"Ride1",53:"RideBell",57:"Crash2"}
for i, inst in enumerate(pm.instruments):
    print(f"-- inst[{i}] is_drum={inst.is_drum} program={inst.program} n_notes={len(inst.notes)}")
    cnt = collections.Counter(n.pitch for n in inst.notes)
    for pitch, c in sorted(cnt.items()):
        print(f"   pitch {pitch} ({GM.get(pitch,'?')}): {c}")
    print("   first 16 onsets(s):", [round(n.start,3) for n in sorted(inst.notes, key=lambda x:x.start)[:16]])
