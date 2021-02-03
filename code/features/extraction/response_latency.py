from typing import Union, Dict, Any, Tuple, List
from neo_importers.neo_wrapper import MNGRecording, ActionPotentialWrapper, ChannelWrapper, ElectricalStimulusWrapper
from features.extraction.feature_extractor import FeatureExtractor
from features.feature import Feature
from quantities import Quantity, s
import numpy as np

class ResponseLatencyFeatureExtractor(FeatureExtractor):

    def __init__(self, recording: MNGRecording, stimulus_channel: str):
        super().__init__(recording)
        self.stimulus_channel: ChannelWrapper = recording.electrical_stimulus_channels[stimulus_channel]
        self.stimulus_indices: List[int] = None
    
    def feature_name(self) -> str:
        return "response_latency"
    
    def feature_shape(self) -> Union[int, tuple]:
        # only the latency
        return 1
    
    def feature_units(self) -> Quantity:
        # in seconds
        return 1*s

    def feature_annotations(self) -> Dict[str, Any]:
        assert self.stimulus_indices is not None
        return {
            "stimulus_channel": self.stimulus_channel.id,
            "stimulus_indices": self.stimulus_indices
        }

    def compute_feature_datapoint(self, action_potential: ActionPotentialWrapper) -> Quantity:
        assert self.stimulus_indices is not None

        stim_idx = self.stimulus_indices[action_potential.index]
        # for some APs, there might not be a previous stimulus
        if stim_idx == -1:
            return np.nan * s
        else:
            stimulus = self.stimulus_channel[stim_idx]
            return action_potential.time - stimulus.time
    
    # search the last stimuli for each action potential
    def _compute_last_stimuli(self, channel: ChannelWrapper) -> List[int]:
        result: List[int] = []
        last_ev = 0
        for action_potential in self.current_channel:
            # use -1 as placeholder if there are no previous events
            # otherwise, we cannot assign NaN latency for APs without previous stimulation
            ev_idx = -1
            # Not using enumerate due to performance reasons
            # if the performance is still to low, scrap the wrapper and work on the
            # neo datastructure directly
            for i in range(last_ev, len(self.stimulus_channel)):
                stimulus: ElectricalStimulusWrapper = self.stimulus_channel[i]
                # we search the first event that was at a later point
                if stimulus.time > action_potential.time:
                    # the last event was the one before
                    ev_idx = i - 1
                    break
            # if we found any event, we can assume that all further APs also have a previous event
            if ev_idx != -1:
                # as the events are (hopefully) sorted, we can skip what we already passed
                last_ev = ev_idx + 1
            result.append(ev_idx)
        return result

    def prepare_extraction(self) -> None:
        # compute the corresponding stimuli
        self.stimulus_indices = self._compute_last_stimuli(self.current_channel)
    
    def finalize_feature(self, feature: Feature) -> Feature:
        self.stimulus_indices = None
        return feature