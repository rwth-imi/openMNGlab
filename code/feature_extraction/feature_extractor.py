from abc import ABC, abstractmethod
from signal_artifacts import ActionPotential

## This is an interface for feature extraction methods.
# We use this interface to ensure that all the feature extractors are "well-behaving".
class FeatureExtractor(ABC):
	## This method should return the name of the feature.
    # This name is also used for access to the dictionary of the AP.
    @abstractmethod
    def get_feature_name() -> str:
        pass
    
	## This function should return the value of the feature for the given AP.
    @abstractmethod
    def get_feature_value(ap: ActionPotential):
        pass