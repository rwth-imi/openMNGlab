from typing import Union, Dict, Any, Tuple
from abc import ABC, abstractmethod
from neo_importers.neo_wrapper import MNGRecording, ActionPotentialWrapper, ChannelWrapper
from features.feature import Feature
from quantities import Quantity
import numpy as np

### Baseclass for feature extraction. To implement a feature extractor, all abstract methods need to be overriden
class FeatureExtractor(ABC):

    def __init__(self, recording: MNGRecording):
        self.recording: MNGRecording = recording
        # This will be set during a feature extraction, so you can access channel specific information
        self.current_channel: ChannelWrapper = None
    
    # Returns the name of the feature as stored in the database
    @abstractmethod
    def feature_name(self) -> str:
        pass
    
    # The shape, i.e. dimensionality of each datapoint
    # 1 dimensional feature with 2 entries should return a 2
    # a 2 dimensional feature with 2 entries (i.e. 2x2 matrix) should return (2, 2)
    # should always return the same value for the same channel, as it might get called
    # multiple times for the same feature
    @abstractmethod
    def feature_shape(self) -> Union[int, tuple]:
        pass
    
    # The units of the feature, for dimensionless just return Quantity(1.)
    # for seconds return 1*s (with s imported from quantities package)
    # you can't mix datatypes with units, so if you need things like None, use dimensionless instead
    @abstractmethod
    def feature_units(self) -> Quantity:
        pass
    
    # compute the feature datapoint as a quantity, that, while not necessarily need to be in the feature_units,
    # the unit its in must at least be convertable to that unit
    # also the shape must conform to the feature_shape. If the shape is "smaller", fill the rest with 0 or None or so
    @abstractmethod
    def compute_feature_datapoint(self, action_potential: ActionPotentialWrapper) -> Quantity:
        pass

    # return the datatype of the underlying data. Default: float
    def feature_dtype(self) -> np.dtype:
        return np.dtype(float)

    # return a dict of annotations to be added to the feature. It can only contain base types, dicts and lists
    # basically anything that can directly be serialize. No complex objects are allowed, but containers can be nested if needed
    def feature_annotations(self) -> Dict[str, Any]:
        return {}
    
    # This is called after current_channel has been set but before the feature is created
    # this can be used to initialize class variables that are needed during each step, or during
    # the feature_... methods above
    def prepare_extraction(self) -> None:
        pass
    
    # This is called after the feature was created but before current_channel is reset
    # use this to cleanup afterwards or to do last changes to the feature
    def finalize_feature(self, feature: Feature) -> Feature:
        return feature
    
    # creates a feature instance. Override this if you want to construct a different class
    def create_feature_instance(self) -> Feature:
        shape = self.feature_shape()
        name = self.feature_name()
        units = self.feature_units()
        dtype = self.feature_dtype()
        annotations = self.feature_annotations()
        return Feature(name, self.recording, self.current_channel.id, \
                       units=units, datapoint_shape=shape, \
                       data_type=dtype, annotations=annotations)

    def create_feature(self, channel_id: str) -> Feature:
        self.current_channel = self.recording.action_potential_channels[channel_id]
        try:
            self.prepare_extraction()
            feature = self.create_feature_instance()
            shape = self.feature_shape()
            for action_potential in feature.channel:
                datapoint = self.compute_feature_datapoint(action_potential)
                assert datapoint.shape == (() if shape == 1 \
                                        else (shape,) if isinstance(shape, int) \
                                        else shape)
                feature[action_potential] = datapoint
            feature = self.finalize_feature(feature)
        finally:
            self.current_channel = None
        return feature