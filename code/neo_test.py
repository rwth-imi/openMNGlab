from pathlib import Path

import neo
import neo_importers.neo_spike_importer as spike_importer
from neo_importers.neo_wrapper import MNGRecording
from features import FeatureDatabase, Feature, ResponseLatencyFeatureExtractor

file_name = Path("..")/"Files"/"latency_experiment_roberto"/"20_05_13_U1a_pulse_Latenz.smr"

bl = spike_importer.import_spike_file(file_name, 
                                      stimuli_event_channels={"DigMark"},
                                      action_potential_channels={"nw-1#2"}
                                      )
seg: neo.core.Segment = bl.segments[0]
wrapper = MNGRecording(bl.segments[0])
db = FeatureDatabase(Path("features"), wrapper)
db.extract_features("ap.0", ResponseLatencyFeatureExtractor, stimulus_channel="es.0")
db.store()
db = FeatureDatabase(Path("features"), wrapper)
db.load()
feature = db["ap.0", "response_latency"]
for ap in wrapper.action_potential_channels["ap.0"]:
    print(ap.time, feature[ap])