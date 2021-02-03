from features.feature import Feature
from typing import Union
from neo_importers.neo_wrapper import MNGRecording, ActionPotentialWrapper
from features.extraction.feature_extractor import FeatureExtractor
from quantities import Quantity
import numpy as np

## Extractor class for the regular spike count with equally sized intervals
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

    # perform some clean-up
    def finalize_feature(self, feature: Feature) -> Feature:
        del self.ap_times
        return super().finalize_feature(feature)

## Builds a feature vector that saves the number of action potentials for each sub-interval.
# The sub-intervals are constructed as follows: \n
# 1.) divide the whole interval defined by the timeframe into two equal parts \n
# 2.) then, divide the rightmost part into two equally sized sub-intervals \n
# 3.) repeat for (num_intervals - 1) times \n\n
# This may result in a vector of a shape like this: \n
# 100s with 6 intervals results in values for the following pre-AP time frames \n
# intervals |100s|50s|25s|12.5s|6.25s|3.125s| \n
# (15, 7, 4, 2, 1, 3)
class AdaptiveSpikeCountExtractor(SpikeCountExtractor):

    def feature_name(self) -> str:
        return "adaptive_spike_count"

    ## Calculate the spike count feature.
    # Subdivide the timeframe before the action potential into several small fragments, then count the number of APs in each of these fragments.
    def compute_feature_datapoint(self, action_potential: ActionPotentialWrapper) -> Quantity:

        t_min = action_potential.time - self.timeframe
        interval_len = self.timeframe / 2.0
        # pre-allocate
        spike_counts = np.zeros(shape = (self.num_intervals, ), dtype = np.int)

        for interval_idx in range(self.num_intervals):
            # calculate spike count and advance to next interval
            spike_counts[interval_idx] = len(self.ap_times[(self.ap_times > t_min) & (self.ap_times < t_min + interval_len)])
            # half the interval length and increase starting time
            interval_len = interval_len / 2.0
            t_min += interval_len

        return spike_counts * self.feature_units()