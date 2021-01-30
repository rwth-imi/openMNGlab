from typing import Union, List, Dict, Any
from neo_importers.neo_wrapper import MNGRecording, ChannelWrapper, ActionPotentialWrapper
from quantities import Quantity
from io import RawIOBase
import numpy as np
from copy import deepcopy

# for loading and storing units as strings
def serialize_units(units: Quantity) -> str:
    return str(units.dimensionality)

def deserialize_units(units: str) -> Quantity:
    return Quantity(1., units=units)

class Feature:
    def __init__(self, recording: MNGRecording, channel_id: str,
                 data: Quantity = None, units: Quantity=None,
                 datapoint_shape: Union[int, tuple]=None,
                 data_type: np.dtype=None,
                 annotations: Dict[str, Any]=None):
        self.recording: MNGRecording = recording
        self.channel: ChannelWrapper = recording.action_potential_channels[channel_id]
        self.annotations: Dict[str, Any] = deepcopy(annotations) if annotations is not None else {}
        if data is not None:
            self.data: Quantity = data
            self.units: Quantity = data.units
        elif datapoint_shape is not None:
            assert data_type is not None
            if units is None:
                units = Quantity(1.) # dimensionless
            data_shape = len(self.channel) if datapoint_shape == 1 \
                    else (len(self.channel), datapoint_shape) if isinstance(datapoint_shape, int) \
                    else (len(self.channel), *data_shape) # tuple
            self.data = np.zeros(data_shape, dtype=data_type) * units
            self.units = units

    def __getitem__(self, key: Union[ActionPotentialWrapper, int, slice, tuple]) -> Quantity:
        if isinstance(key, ActionPotentialWrapper):
            return self.data[key.index]
        if isinstance(key, tuple):
            # multidimensional access, first get the first dimension (as this can be the AP class)
            # then get the dimensionality part from it
            return self.data[key[0]][key[1:]]
        return self.data[key]

    def __setitem__(self, key: Union[ActionPotentialWrapper, int, slice], value: Quantity) -> None:
        val = value.rescale(self.units)
        if isinstance(key, ActionPotentialWrapper):
            self.data[key.index] = val
        else:
            self.data[key] = val
    
    def store_data(self, stream: RawIOBase) -> None:
        np.save(stream, self.data)
    
    def load_data(self, stream: RawIOBase, units: Quantity) -> None:
        # units need to be stored seperately
        self.data = np.load(stream) * units
        self.units = units
