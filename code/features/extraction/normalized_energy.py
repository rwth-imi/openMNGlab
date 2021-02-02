from neo_importers.neo_wrapper import MNGRecording, ActionPotentialWrapper
from features.extraction.feature_extractor import FeatureExtractor
from typing import Union
from quantities import Quantity, millivolt
import numpy as np

## Calculates the normalized signal energy for an action potential
class NormalizedSignalEnergyExtractor(FeatureExtractor):

    def __init__(self, recording: MNGRecording):
        super().__init__(recording)

    def feature_name(self) -> str:
        return "normalized_energy"
    
    def feature_shape(self) -> Union[int, tuple]:
        return 1
    
    def feature_units(self) -> Quantity:
        return millivolt**2

	## Calculates the normalized signal energy for the given AP.
	# 1.) sum the squared signal values and
	# 2.) divide by the number of values for normalization
	# @param action_potential The AP for which the normalized energy is calculated.
    def compute_feature_datapoint(self, action_potential: ActionPotentialWrapper) -> Quantity:
        return np.sum(np.square(action_potential.raw_signal)) / len(action_potential.raw_signal)