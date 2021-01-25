from pathlib import Path

import neo
import neo_importers.neo_spike_importer as spike_importer
from neo_importers.neo_wrapper import MNGRecording

file_name = Path("..")/"Files"/"latency_experiment_roberto"/"20_05_13_U1a_pulse_Latenz.smr"

bl = spike_importer.import_spike_file(file_name, 
                                      stimuli_event_channels={"DigMark"},
                                      action_potential_channels={("nw-1#2", "DigMark")}
                                      )
seg: neo.core.Segment = bl.segments[0]
wrapper = MNGRecording(bl.segments[0])
ap_channel = wrapper.action_potential_channels["ap.0"]
for ap in ap_channel[10::-1]:
    print(ap.time, ap.stimulus.time, ap.stimulus_response_time)