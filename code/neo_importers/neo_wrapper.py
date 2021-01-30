from typing import Dict, Iterable, Union, List, Type
from abc import ABC
from enum import Enum

from neo.core import Event, Epoch, AnalogSignal, SpikeTrain, Segment
from neo.core.dataobject import DataObject
from quantities import Quantity

class TypeID(Enum):
    RAW_DATA = "rd" # analogsignal channel
    ACTION_POTENTIAL = "ap" # spiketrain channel
    ELECTRICAL_STIMULUS = "es" # event channel
    ELECTRICAL_EXTRA_STIMULUS = "ex" # epoch channel
    MECHANICAL_STIMULUS = "ms" #spiketrain channel

def _index_channels(channels: Iterable[DataObject], type_filter: TypeID) -> Dict[str, DataObject]:
    return {
        channel.annotations["id"]: channel for channel in channels if channel.annotations.get("type_id") == type_filter.value
    }

class ChannelDataWrapper(ABC):
    # To ensure polymorphic creation all subclasses must have the same constructor signature
    # The call to the super constructor itself is not necessary if these fields are not required
    def __init__(self, recording: "MNGRecording", channel: DataObject, index: int):
        self.recording: MNGRecording = recording
        self.channel: DataObject = channel
        self.index: int = index

class ActionPotentialWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", ap_channel: SpikeTrain, ap_index: int):
        super().__init__(recording, ap_channel, ap_index)
        self.time: Quantity = ap_channel.times[ap_index]
        self.raw_signal: Quantity = ap_channel.waveforms[ap_index, 0]
        self.duration: Quantity = len(self.raw_signal) * ap_channel.sampling_period

class ElectricalStimulusWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", es_channel: Event, es_index: int):
        super().__init__(recording, es_channel, es_index)
        self.time: Quantity = es_channel.times[es_index]
        self.interval: Quantity = es_channel.array_annotations["intervals"][es_index]

class ElectricalExtraStimulusWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", ex_channel: Epoch, ex_index: int):
        super().__init__(recording, ex_channel, ex_index)
        self.time: Quantity = ex_channel.times[ex_index]
        self.duration: Quantity = ex_channel.durations[ex_index]
        self.frequency: Quantity = ex_channel.array_annotations["frequency"][ex_index]

class MechanicalStimulusWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", ms_channel: SpikeTrain, ms_index: int):
        super().__init__(recording, ms_channel, ms_index)
        self.time: Quantity = ms_channel.times[ms_index]
        self.raw_signal: Quantity = ms_channel.waveforms[ms_index, 0]
        self.duration: Quantity = len(self.raw_signal) * ms_channel.sampling_period
        self.amplitude: Quantity = ms_channel.array_annotations["amplitudes"][ms_index]

class DataWrapperIterator:
    def __init__(self, channel: "ChannelWrapper"):
        self.channel: ChannelWrapper = channel
        self.length: int = len(channel.channel)
        self.index: int = 0
    
    def __iter__(self):
        self.index = 0
        return self
    
    def __next__(self):
        if self.index >= self.length:
            raise StopIteration()
        # Polymorphically create the wrapper class
        result = self.channel.wrapper_class(self.channel.recording, self.channel.channel, self.index)
        self.index += 1
        return result

# Maybe we want to implement the polymorphism via generics (however they may work in python)
# so we can make use of type annotations, like for the iterator
# Because currently it *hugs* pretty badly that vscode (and probably other editors/ides) 
# does not recognize the type of the iterated object and can't give auto completions 
class ChannelWrapper:
    def __init__(self, recording: "MNGRecording", channel: DataObject, wrapper_class: Type[ChannelDataWrapper]):
        self.recording: MNGRecording = recording
        self.channel: DataObject = channel
        self.wrapper_class: Type[ChannelDataWrapper] = wrapper_class
        self.id: str = channel.annotations["id"]
        self.type_id: TypeID = TypeID(channel.annotations["type_id"])

    # make this a container like object, see:
    # https://docs.python.org/3/reference/datamodel.html#emulating-container-types
    def __len__(self) -> int:
        # as all channels are basically glorified nparrays this is easy
        return len(self.channel)
    
    def __getitem__(self, key: int) -> Union[ActionPotentialWrapper, List[ActionPotentialWrapper]]:
        # FIXME: due to performance reasons (as this creates all wrappers at once) this should be rewritten
        # returning an iterator that crates these instances when requested
        if isinstance(key, slice):
            return [self.wrapper_class(self.recording, self.channel, index) for index in range(*key.indices(len(self)))]
        if not isinstance(key, int):
            raise TypeError()
        # all error checking with regards to the index/key will be done by numpy
        # when accessing the data in the ActionPotentialWrapper constructor
        return self.wrapper_class(self.recording, self.channel, key)

    # setitem and delitem are skipped we don't need them

    def __iter__(self):
        return DataWrapperIterator(self)
        

class MNGRecording:
    def __create_channel_wrappers(self, channels: Dict[str, DataObject], wrapper_class: Type[ChannelDataWrapper]) -> Dict[str, ChannelWrapper]:
        return {
            channel_id: ChannelWrapper(self, channel, wrapper_class) for channel_id, channel in channels.items()
        }

    def __init__(self, segment: Segment, name: str="UNNAMED", file_name: str=None):
        self.segment: Segment = segment

        self.name: str = name
        self.file_name: str = file_name

        # indexing data for fast access
        self.all_channels: Dict[str, DataObject] = {
            channel.annotations["id"]: channel for channel in segment.data_children if "id" in channel.annotations
        }

        self.raw_data_channels_raw: Dict[str, AnalogSignal] = _index_channels(segment.analogsignals, TypeID.RAW_DATA)
        self.action_potential_channels_raw: Dict[str, SpikeTrain] = _index_channels(segment.spiketrains, TypeID.ACTION_POTENTIAL)
        self.electrical_stimulus_channels_raw: Dict[str, Event] = _index_channels(segment.events, TypeID.ELECTRICAL_STIMULUS)
        self.electrical_extra_stimulus_channels_raw: Dict[str, Epoch] = _index_channels(segment.events, TypeID.ELECTRICAL_EXTRA_STIMULUS)
        self.mechanical_stimulus_channels_raw: Dict[str, SpikeTrain] = _index_channels(segment.spiketrains, TypeID.MECHANICAL_STIMULUS)

        # access wrappers
        self.raw_data_channels = self.raw_data_channels_raw.copy()
        self.action_potential_channels: Dict[str, ChannelWrapper] = \
            self.__create_channel_wrappers(self.action_potential_channels_raw, ActionPotentialWrapper)
        self.electrical_stimulus_channels: Dict[str, ChannelWrapper] = \
            self.__create_channel_wrappers(self.electrical_stimulus_channels_raw, ElectricalStimulusWrapper)
        self.electrical_extra_stimulus_channels: Dict[str, ChannelWrapper] = \
            self.__create_channel_wrappers(self.electrical_extra_stimulus_channels_raw, ElectricalExtraStimulusWrapper)
        self.mechanical_stimulus_channels: Dict[str, ChannelWrapper] = \
            self.__create_channel_wrappers(self.mechanical_stimulus_channels_raw, MechanicalStimulusWrapper)
    
    def __getitem__(self, key: str) -> AnalogSignal:
        return self.all_channels.get(key)
