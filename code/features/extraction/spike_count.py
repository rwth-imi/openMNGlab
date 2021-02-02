from typing import Union
from neo_importers.neo_wrapper import MNGRecording, ActionPotentialWrapper
from features.extraction.feature_extractor import FeatureExtractor
from quantities import Quantity
import numpy as np

class SpikeCountExtractor(FeatureExtractor):

    def __init__(self, recording: MNGRecording, num_intervals: int, timeframe: float):
        super().__init__(recording)

        self.num_intervals = num_intervals
        self.timeframe = timeframe

    def feature_name(self) -> str:
        return "spike_count"

    def feature_dtype(self) -> np.dtype:
        return np.ndarray

    def feature_shape(self) -> Union[int, tuple]:
        return (self.num_intervals, )

    def feature_units(self) -> Quantity:
        return Quantity(1.)

    ## Calculate the spike count feature.
    # Subdivide the timeframe before the action potential into several small fragments, then count the number of APs in each of these fragments.
    def compute_feature_datapoint(self, action_potential: ActionPotentialWrapper) -> Quantity:

        t_min = action_potential.time - self.timeframe
        interval_len = self.timeframe / self.num_intervals
        # pre-allocate
        spike_counts = np.zeros(shape = (self.num_intervals, ), dtype = np.int)

        for interval_idx in range(self.num_intervals):
            # calculate spike count and advance to next interval
            spike_counts[interval_idx] = len(self.ap_times[(self.ap_times > t_min) & (self.ap_times < t_min + interval_len)])
            t_min += interval_len

        return spike_counts * self.feature_units()

    ## Here, we collect all APs in a single list s.t. we can compute the spike count later
    def prepare_extraction(self) -> None:
        # keeps arrays of ap times for each channel
        all_ap_times = []
        # 
        for _, channel in self.recording.action_potential_channels.items():
            
            aps = [ap for ap in channel]
            ap_times = np.zeros(shape = (len(aps), ), dtype = np.float)
            
            # write all times for this channel into an array
            ap: ActionPotentialWrapper
            for idx, ap in enumerate(aps):
                ap_times[idx] = ap.time

            all_ap_times.append(ap_times)

        # merge
        self.ap_times = np.concatenate(all_ap_times)
        self.ap_times.sort()

        print(self.ap_times)