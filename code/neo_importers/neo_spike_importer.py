from pathlib import Path
from typing import Dict, List, Set, Iterable, Union, Tuple, Callable
from neo.core import Block, Segment, SpikeTrain, Event, AnalogSignal, Group
from neo.core.dataobject import DataObject
from neo.io import Spike2IO
from numpy import ndarray as NPArray
from enum import Enum
import numpy as np
import re

#################################################################################################
## General information:                                                                        ##
## This importer loads Spike2 files, and prepares them the following was:                      ##
## * all *imported* datastructures get annotated with the channel_id property. This is the     ##
##   spike internal channel number - 1 (as spike numbers are 1 based but ids are 0 based)      ##
## * datastructures representing usable data get annotated with the id property,               ##
##   a unique string identifying the channel. The format will be {type_id}.{index} where       ##
##   - type_id is the string representation of a value from the TypeID enum                    ##
##   - index is an incrementing numerical value for each                                       ##
##   The type_id will be also annotated seperately                                             ##
## * all names will be made made unique. If 2 channels have the same name, they will get an    ##
##   index appended like foo_1 and foo_2 for two channels named foo. For spiketrains the       ##
##   marker filter will be added to the channel behind a #. The original name will be          ##
##   stored as annotation with the name "original_name"                                        ##
#################################################################################################

class TypeID(Enum):
    RAW_DATA = "rd"
    ACTION_POTENTIAL = "ap"
    ELECTRICAL_STIMULUS = "es"
    ELECTRICAL_EXTRA_STIMULUS = "ex"
    MECHANICAL_STIMULUS = "ms"
    CHANNEL = "ch"

################################## Types ##################################
# Either channel id or channel name
ChannelReference = Union[str, int]

SpikeFilterReference = int
# Either a channel if there is only one filter that is non empty, or a channel, filter tuple
SpikeChannelReference = Union[ChannelReference, ChannelReference, SpikeFilterReference]
# Either a set of the references, or a dict mapping channel references on filters
SpikeChannelReferences = Union[Set[SpikeChannelReference], Dict[ChannelReference, Set[SpikeFilterReference]]]

EventMarker = str
# Either a channel if all events of that channel are referenced, otherwise a channel, marker tuple
EventChannelReference = Union[ChannelReference, Tuple[ChannelReference, EventMarker]]
# Either just a set of references, or a dict matching channel names to matching event markers
EventChannelReferences = Union[Set[EventChannelReference], Dict[ChannelReference, Set[EventMarker]]]

############################# General helpers #############################

def _store_original_names(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        obj.annotate(original_name=obj.name)

def _make_names_unique(objects: Iterable[DataObject]) -> None:
    objects_by_name: Dict[str, List[DataObject]] = {obj.name: [o for o in objects if o.name == obj.name] for obj in objects}
    for obj_list in objects_by_name.values():
        if len(obj_list) > 1:
            for i, obj in enumerate(obj_list):
                obj.name = f"{obj.name}_{i}"

def _normalize_event_channel_references(references: EventChannelReferences) -> Set[EventChannelReference]:
    if isinstance(references, set):
        return references
    result: Set[EventChannelReference] = {}
    for ch_ref, markers in references.values():
        result.update([(ch_ref, marker) for marker in markers])
    return result

def _channel_by_reference(channels: Iterable[DataObject], ref: ChannelReference) -> DataObject:
    for channel in channels:
        if (isinstance(ref, str) and channel.name == ref) \
            or (isinstance(ref, int) and channel.annotations.get("channel_id", None) == ref):
            return channel
    return None

############################# Spiketrains #############################

# Takes a list of spiketrains and groups them by the channel they reference
# This way we can distinguish channels with the same name
def _group_spiketrains_by_channel_ref(spiketrains: List[SpikeTrain]) -> Dict[int, List[SpikeTrain]]:
    result: Dict[int, List[SpikeTrain]] = {}
    # The Spike2IO reader adds a unique ID to each spiketrain of the form chID#Filter
    # ID is the ID of the channel (spike channel number -1) and filter is the marker filter
    # So the waveforms in the spike channel N is the union of all waveforms of ch(N-1)#J for all J
    id_expr = re.compile("ch(\\d+)#(\\d+)")
    for spiketrain in spiketrains:
        match = id_expr.match(spiketrain.annotations["id"])
        assert match is not None
        ch_id = int(match.group(1))
        marker_filter = int(match.group(2))
        # Annotate the spiketrain with the information which channel it references and what markers are filtered
        spiketrain.annotate(channel_id=ch_id, marker_filter=marker_filter)
        # group this spiketrain to it's corresponding channel
        channel_spiketrains = result.get(ch_id, [])
        channel_spiketrains.append(spiketrain)
        result[ch_id] = channel_spiketrains
    return result

# If two or more channels have the same name, make the name unique by adding an index to the name
def _make_spiketrain_names_unique_per_channel(spiketrain_channels: List[List[SpikeTrain]]) -> None:
    if len(spiketrain_channels) == 1:
        return
    for i, spiketrains in enumerate(spiketrain_channels):
        for spiketrain in spiketrains:
            spiketrain.name = f"{spiketrain.name}_{i}"

# Make different marker filter spiketrain names unique by appending their marker ID to the name
def _make_spiketrain_names_unique_per_marker(spiketrains: List[SpikeTrain]) -> None:
    for spiketrain in spiketrains:
        spiketrain.name = f"{spiketrain.name}#{spiketrain.annotations['marker_filter']}"

def _prepare_spiketrains(segment: Segment) -> None:
    # lists of all spiketrains with the same name
    channels: Dict[str, List[SpikeTrain]] = {st.name: [s for s in segment.spiketrains if s.name == st.name] for st in segment.spiketrains}
    for spiketrains in channels.values():
        channel_refs = _group_spiketrains_by_channel_ref(spiketrains)
        _make_spiketrain_names_unique_per_channel(channel_refs.values())
        _make_spiketrain_names_unique_per_marker(spiketrains)

############################# Events #############################

def _assign_event_channel_ids(events: List[Event]) -> None:
    for event in events:
        event.annotate(channel_id=event.annotations["id"])

def _prepare_events(segment: Segment) -> None:
    events: List[Event] = segment.events
    _make_names_unique(events)
    _assign_event_channel_ids(events)

def _remove_empty_names(objects: Iterable[DataObject]) -> None:
    for obj in objects:
        if obj.name is None or not obj.name:
            obj.name = "UNNAMED"

############################# Semantic datastructures #############################

############################# Electrical stimuli #############################

def _filter_event_channel(event_channel: Event, label_filter: Callable[[str], bool]) -> Event:
    # list or ndarray
    labels = event_channel.labels
    # always an ndarray
    times: NPArray = event_channel.times
    matches = label_filter(labels) if isinstance(labels, NPArray) \
         else [label_filter(l) for l in labels]
    
    new_times = times[matches]
    new_labels = labels[matches] if isinstance(labels, NPArray) \
        else [l for l in labels if label_filter(l)]
    return Event(times=new_times, labels=new_labels, units=event_channel.units)

def _create_filter_channel(segment: Segment, channel_ref: ChannelReference, marker: EventMarker) -> Event:
    channel = _channel_by_reference(segment.events, channel_ref)
    assert channel is not None
    # Create new channel by filtering all where the label is the marker
    new_channel = _filter_event_channel(channel, lambda label: label==marker)
    # add the marker to the name to make it unique
    new_channel.name = f"{channel.name}#{marker}"
    # add information about the fork to the newly created channel
    new_channel.annotate(forked_from=channel.name, marker=marker)
    # Add the channel to the segment
    segment.events.append(new_channel)
    return new_channel

# First, detect stimuli event channels, if necessary split them up by their marker
# Second, create stimuli interval channels for each stimuli channel
def _prepare_stimuli(segment: Segment, stimuli_channels: EventChannelReferences) -> None:
    if stimuli_channels is None:
        return
    channels = _normalize_event_channel_references(stimuli_channels)
    stimulus_index = 0
    for ev_ref in channels:
        # Get the referenced channel
        channel: Event = None
        if isinstance(ev_ref, tuple):
            # and if it is a "part" channel, create it first
            ch_ref, marker = ev_ref
            channel = _create_filter_channel(segment, ch_ref, marker)
        else:
            channel = _channel_by_reference(segment.events, ev_ref)
        assert channel is not None
        # generate id
        type_id = TypeID.ELECTRICAL_STIMULUS.value
        channel_id = f"{type_id}.{stimulus_index}"
        stimulus_index += 1
        channel.annotate(id=channel_id, type_id=type_id)
        # compute intervals
        # this list will be shorter by 1 then the stimuli list
        # the reason for this is that there are only intervals between
        # the events, i.e. neither include the time from t0 to event 1
        # nor the timeframe from the last event to the end of the experiment
        intervals = np.diff(channel.times)
        channel.array_annotate(intervals=intervals)

############################# Raw data #############################

def _prepare_raw_data(segment: Segment, raw_channels: Set[ChannelReference]) -> None:
    if raw_channels is None:
        raw_channels = {a.name for a in segment.analogsignals}
    index = 0
    type_id = TypeID.RAW_DATA.value
    for channel_ref in raw_channels:
        channel = _channel_by_reference(segment.analogsignals, channel_ref)
        channel_id = f"{type_id}.{index}"
        index += 1
        channel.annotate(id=channel_id, type_id=type_id)

############################# Loading #############################

def _prepare_segment(segment: Segment) -> None:
    _remove_empty_names(segment.data_children)
    _store_original_names(segment.data_children)
    _prepare_spiketrains(segment)
    _prepare_events(segment)

# deletes all unnecessary channels
def _prune_segment(segment: Segment) -> None:
    segment.analogsignals = [a for a in segment.analogsignals if "type_id" in a.annotations]
    segment.epochs = [ep for ep in segment.epochs if "type_id" in ep.annotations]
    segment.events = [ev for ev in segment.events if "type_id" in ev.annotations]
    segment.irregularlysampledsignals = [i for i in segment.irregularlysampledsignals if "type_id" in i.annotations]
    segment.spiketrains = [st for st in segment.spiketrains if "type_id" in st.annotations]
    segment.imagesequences = [i for i in segment.imagesequences if "type_id" in i.annotations]

def import_spike_file(file_name: Path,
                      stimuli_event_channels: EventChannelReferences = None,
                      raw_channels: Set[ChannelReference] = None) -> Block:
    spikeio = Spike2IO(filename=str(file_name.resolve()))
    blocks = spikeio.read(lazy=False, load_waveforms=True)
    spike_data = blocks[0]
    for segment in spike_data.segments:
        _prepare_segment(segment)
        _prepare_raw_data(segment, raw_channels)
        _prepare_stimuli(segment, stimuli_event_channels)
        _prune_segment(segment)
    return spike_data