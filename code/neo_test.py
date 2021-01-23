from pathlib import Path

import neo
import neo_importers.neo_spike_importer as spike_importer

file_name = Path("..")/"Files"/"latency_experiment_roberto"/"20_05_13_U1a_pulse_Latenz.smr"

bl = spike_importer.import_spike_file(file_name, 
                                      stimuli_event_channels={"DigMark"},
                                      action_potential_channels={("nw-1#2", "DigMark")}
                                      )
seg: neo.core.Segment = bl.segments[0]
for a in seg.data_children:
    print(a.name, ":", a.annotations)