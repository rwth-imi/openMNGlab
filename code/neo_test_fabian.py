from pathlib import Path

import neo
import neo_importers.neo_spike_importer as spike_importer
from neo_importers.neo_wrapper import ActionPotentialWrapper, MNGRecording, ChannelWrapper
from features import FeatureDatabase, Feature, ResponseLatencyFeatureExtractor, NormalizedSignalEnergyExtractor, SpikeCountExtractor
from quantities import second

file_name = Path("..")/".."/"Files"/"11_10_27U2a.smr"

bl = spike_importer.import_spike_file(file_name, 
                                      stimuli_event_channels={"DigMark"},
                                      action_potential_channels={"nw-1_0#1", "nw-1_0#2", "nw-1_0#3", "nw-1_0#4", "nw-1_0#5"}
                                      )
seg: neo.core.Segment = bl.segments[0]
wrapper = MNGRecording(bl.segments[0])


print(wrapper.all_channels.keys())

db = FeatureDatabase(Path("features"), wrapper)
db.extract_features("ap.0", ResponseLatencyFeatureExtractor, stimulus_channel="es.0")
db.extract_features("ap.0", NormalizedSignalEnergyExtractor)
db.extract_features("ap.0", SpikeCountExtractor, timeframe = 100 * second, num_intervals = 8)
db.store()
db = FeatureDatabase(Path("features"), wrapper)
db.load()

feature = db["ap.0", "spike_count"]
# feature = db["ap.0", "normalized_energy"]
# feature = db["ap.0", "response_latency"]
for ap in wrapper.action_potential_channels["ap.0"]:
    print(ap.time, feature[ap])
