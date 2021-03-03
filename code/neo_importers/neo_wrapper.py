from typing import Dict, Iterable, Union, List, Type
from abc import ABC
from enum import Enum

from neo.core import Event, Epoch, AnalogSignal, SpikeTrain, Segment
from neo.core.dataobject import DataObject
from quantities import Quantity, ms

## Enum for the different channel types in our unified format
class TypeID(Enum): 
    RAW_DATA = "rd" # analogsignal channel
    ACTION_POTENTIAL = "ap" # spiketrain channel
    ELECTRICAL_STIMULUS = "es" # event channel
    ELECTRICAL_EXTRA_STIMULUS = "ex" # epoch channel
    MECHANICAL_STIMULUS = "ms" #spiketrain channel

## Get a lookup dictionary for channel ids to channel objects of a given type
#  @param channels iterable container containing all channels
#  @param type_filter the TypeID value to filter  for
#  @returns a lookup table mapping channel ids to their channels
def _index_channels(channels: Iterable[DataObject], type_filter: TypeID) -> Dict[str, DataObject]:
    return {
        channel.annotations["id"]: channel for channel in channels if channel.annotations.get("type_id") == type_filter.value
    }

## Returns an analog channel by it's channel name
#  @param channels iterable container containing the analog channels to search through
#  @param name the name to search for
#  @returns the first found channel matching the name
def _analog_signal_by_name(channels: Iterable[AnalogSignal], name: str) -> AnalogSignal:
    if not isinstance(name, str):
        raise Exception("Can only reference analog signals by name using strings.")
    for channel in channels:
        if channel.name == name:
            return channel
    raise Exception(f"""No raw data channel with name \"{name}\"""")

## Base class for representing a datapoint in a channel
#  Contains the following members:
#  * recording: a reference to the MNG recording this wrapper was created from
#  * channel: a reference to the Neo datastructure this data is from
#  * index: the datapoint index within the neo structure
class ChannelDataWrapper(ABC):
    # To ensure polymorphic creation all subclasses must have the same constructor signature
    # The call to the super constructor itself is not necessary if these fields are not required
    def __init__(self, recording: "MNGRecording", channel: DataObject, index: int):
        self.recording: MNGRecording = recording
        self.channel: DataObject = channel
        self.index: int = index

## Wrapper class representing a single action potential
#  Contains the following members:
#  * time: start time of the ap spike
#  * raw_signal: raw data of the waveform
#  * duration: length of the spike
class ActionPotentialWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", ap_channel: SpikeTrain, ap_index: int):
        super().__init__(recording, ap_channel, ap_index)
        self.time: Quantity = ap_channel.times[ap_index]
        self.raw_signal: Quantity = ap_channel.waveforms[ap_index, 0]
        self.duration: Quantity = len(self.raw_signal) * ap_channel.sampling_period
        self.duration.units = ms

    def __str__(self):
        return (f"""Action potential:\n"""  + 
                f"""Starts at {self.time}\n""" + 
                f"""Duration is {self.duration}\n""")

## Wrapper class representing a single electrical stimulus
#  Contains the following members:
#  * time: start time of the event
#  * interval: the time until the next stimulus
class ElectricalStimulusWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", es_channel: Event, es_index: int):
        super().__init__(recording, es_channel, es_index)
        self.time: Quantity = es_channel.times[es_index]
        self.interval: Quantity = es_channel.array_annotations["intervals"][es_index]

    def __str__(self):
        return (f"""Electrical stimulus:\n"""  + 
                f"""Starts at {self.time}\n""" + 
                f"""Interval length is {self.interval}\n""")

    @property
    def sweep_duration(self):
        return self.interval

    @property
    def sweep_endpoint(self):
        return self.time + self.sweep_duration

## Wrapper class representing a single electrical extra stimulus
#  Contains the following members:
#  * time: start time of the first stimulus of the group
#  * duration: length of the whole stimulus group
#  * frequency: frequency of the stimuli within that interval
class ElectricalExtraStimulusWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", ex_channel: Epoch, ex_index: int):
        super().__init__(recording, ex_channel, ex_index)
        self.time: Quantity = ex_channel.times[ex_index]
        self.duration: Quantity = ex_channel.durations[ex_index]
        self.frequency: Quantity = ex_channel.array_annotations["frequency"][ex_index]

## Wrapper class representing a single mechanical stimulus
#  Contains the following members:
#  * time: start time of the stimulus spike
#  * raw_signal: raw data of the waveform
#  * duration: length of the stimulus
#  * amplitude: maximum amplitude of that stimulus
class MechanicalStimulusWrapper(ChannelDataWrapper):
    def __init__(self, recording: "MNGRecording", ms_channel: SpikeTrain, ms_index: int):
        super().__init__(recording, ms_channel, ms_index)
        self.time: Quantity = ms_channel.times[ms_index]
        self.raw_signal: Quantity = ms_channel.waveforms[ms_index, 0]
        self.duration: Quantity = len(self.raw_signal) * ms_channel.sampling_period
        self.amplitude: Quantity = ms_channel.array_annotations["amplitudes"][ms_index]

## Iterator class allows iterating over a channel and creating the wrapper instances ad-hoc
#  This class should not be used directly, only for iteration in for-in loops
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

## Wrapper class representing a channel in the recording
#  Allows transparent access of the datapoints as wrapper classes
#  Provides container functionality through len, accessing thorugh [index] or [start:stop(:step)] and iterating through for-in
#  Wrapper class instances are only created ad-hoc and not stored in memory 
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
        
## Wrapper class representing a recording session using a Neo segment as data storage
#  Allows access through [channel_id] to the Neo datastructures.
#  Contains the following members:
#  * name: The name of the recording
#  * file_name: the filename this recording was stored in
#  * all_channels: a dictionary mapping channel ids to the Neo channel objects
#  * raw_data_channels_raw: a dictionary mapping the raw data channel ids to the Neo channel objects
#  * action_potential_channels_raw: a dictionary mapping the action potential channel ids to the Neo channel objects
#  * electrical_stimulus_channels_raw: a dictionary mapping the electrical stimulus channel ids to the Neo channel objects
#  * electrical_extra_stimulus_channels_raw: a dictionary mapping the electrical extra stimulus channel ids to the Neo channel objects
#  * mechanical_stimulus_channels_raw: a dictionary mapping the mechanical extra stimulus channel ids to the Neo channel objects
#  * raw_dat_channels: the same as raw_data_channels_raw
#  * action_potential_channels: a dictionary mapping the action potential channel ids to the channel wrapper objects
#  * electrical_stimulus_channels: a dictionary mapping the electrical stimulus channel ids to the channel wrapper objects
#  * electrical_extra_stimulus_channels: a dictionary mapping the electrical extra stimulus channel ids to the channel wrapper objects
#  * mechanical_stimulus_channels: a dictionary mapping the mechanical extra stimulus channel ids to the channel wrapper objects
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

        self.raw_data_channels_raw: Dict[str, AnalogSignal] = {**_index_channels(segment.analogsignals, TypeID.RAW_DATA), \
            **_index_channels(segment.irregularlysampledsignals, TypeID.RAW_DATA)}
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
    
    def __getitem__(self, key: str) -> DataObject:
        return self.all_channels.get(key)

    def raw_data_channel_by_name(self, name: str) -> AnalogSignal:
        return _analog_signal_by_name(channels = self.raw_data_channels.values(), name = name)