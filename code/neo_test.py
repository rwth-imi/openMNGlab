from pathlib import Path

import neo
import neo_importers.neo_spike_importer as spike_importer
from neo_importers.recording_io import load_block, store_block, load_recordings, store_recordings
from neo_importers.neo_wrapper import MNGRecording
from features import FeatureDatabase, Feature, ResponseLatencyFeatureExtractor

file_name = Path("..")/".."/"Files"/"latency_experiment_roberto"/"20_05_13_U1a_pulse_Latenz.smr"

bl, id_map = spike_importer.import_spike_file(file_name, 
                                              stimuli_event_channels={"DigMark"},
                                              action_potential_channels={"nw-1#2"}
                                             )
seg: neo.core.Segment = bl.segments[0]
wrapper = MNGRecording(bl.segments[0])
fname = Path("test.h5")
store_block(fname, bl)
(wrapper2,), id_map2 = load_recordings(fname)

for i in range(10):
    print(wrapper.action_potential_channels["ap.0"][0].raw_signal)
    print(wrapper2.action_potential_channels["ap.0"][0].raw_signal)
