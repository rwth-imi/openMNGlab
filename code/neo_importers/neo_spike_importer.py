from pathlib import Path
from typing import Dict, List, Set, Iterable, Union, Tuple, Callable
from neo.core import Block, Segment, SpikeTrain, Event, AnalogSignal, Group, Epoch
from neo.core.dataobject import DataObject
from neo.io import Spike2IO
from numpy import ndarray as NPArray
from quantities import s, Quantity, Hz
import numpy as np
import re

from neo_importers.neo_wrapper import TypeID

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

################################## Types ##################################
# Either channel id or channel name
ChannelReference = Union[str, int]

SpikeFilterReference = int
# Either a channel if there is only one filter that is non empty, or a channel, filter tuple
SpikeChannelReference = Union[ChannelReference, Tuple[ChannelReference, SpikeFilterReference]]
# Either a set of the references, or a dict mapping channel references on filters
SpikeChannelReferences = Union[Set[SpikeChannelReference], Dict[ChannelReference, Set[SpikeFilterReference]]]

EventMarker = str
# Either a channel if all events of that channel are referenced, otherwise a channel, marker tuple
EventChannelReference = Union[ChannelReference, Tuple[ChannelReference, EventMarker]]
# Either just a set of references, or a dict matching channel names to matching event markers
EventChannelReferences = Union[Set[EventChannelReference], Dict[ChannelReference, Set[EventMarker]]]

# A raw channel is just that, a channel
RawChannelReference = ChannelReference
# Multiple channel references simply as a set
RawChannelReferences = Set[ChannelReference]

# Tuple of raw channel and threshold
MechanicalStimulusReference = Tuple[RawChannelReference, Quantity]
MechanicalStimulusReferences = Set[MechanicalStimulusReference]

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

def _normalize_channel_refs(references: EventChannelReferences) -> Set[EventChannelReference]:
    if isinstance(references, set):
        return references
    result: Set[EventChannelReference] = set()
    for ch_ref, items in references.items():
        result.update([(ch_ref, item) for item in items])
    return result

def _channel_by_reference(channels: Iterable[DataObject], ref: ChannelReference) -> DataObject:
    for channel in channels:
        if (isinstance(ref, str) and channel.name == ref) \
            or (isinstance(ref, int) and channel.annotations.get("channel_id", None) == ref):
            return channel
    return None

def _spiketrain_by_reference(channels: Iterable[SpikeTrain], ref: SpikeChannelReference) -> SpikeTrain:
    if isinstance(ref, str) or isinstance(ref, int):
        return _channel_by_reference(channels, ref)
    ch_ref, spike_filter = ref
    for channel in channels:
        if (isinstance(ch_ref, str) and channel.name == f"{ch_ref}#{spike_filter}") \
            or (isinstance(ch_ref, int) and channel.annotations.get("channel_id", None) == ch_ref \
                and channel.annotations.get("spike_filter", None) == spike_filter):
            return channel

def _event_channel_by_reference(channels: Iterable[Event], ref: EventChannelReference) -> Event:
    if isinstance(ref, str) or isinstance(ref, int):
        return _channel_by_reference(channels, ref)
    ch_ref, marker = ref
    for channel in channels:
        if (isinstance(ch_ref, str) and channel.name == f"{ch_ref}#{marker}") \
            or (isinstance(ch_ref, int) and channel.annotations.get("channel_id", None) == ch_ref \
                and channel.annotations.get("marker", None) == marker):
            return channel

def _quantity_concat(a: Quantity, b: Quantity) -> Quantity:
    return np.concatenate([a, b.rescale(a.units)]) * a.units

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
        spike_filter = int(match.group(2))
        # Annotate the spiketrain with the information which channel it references and what markers are filtered
        spiketrain.annotate(channel_id=ch_id, spike_filter=spike_filter)
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
        spiketrain.name = f"{spiketrain.name}#{spiketrain.annotations['spike_filter']}"

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
    # very dirty hack
    search_marker = str(ord(marker))
    # Create new channel by filtering all where the label is the marker
    new_channel = _filter_event_channel(channel, lambda label: label==search_marker)
    # add the marker to the name to make it unique
    new_channel.name = f"{channel.name}#{marker}"
    # add information about the fork to the newly created channel
    new_channel.annotate(forked_from=channel.name, marker=marker, channel_id=channel.annotations["channel_id"])
    # Add the channel to the segment
    segment.events.append(new_channel)
    return new_channel

# First, detect stimuli event channels, if necessary split them up by their marker
# Second, create stimuli interval channels for each stimuli channel
def _prepare_stimuli(segment: Segment, stimuli_channels: EventChannelReferences) -> None:
    if stimuli_channels is None:
        return
    channels = _normalize_channel_refs(stimuli_channels)
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
        # this will be annotated onto the datapoints, as there are only time intervals between
        # two events, the last one does not have a followup even. Therefore the time interval
        # is infinity
        # Alternative solution would be to have this intervall be one shorter then the datapoints
        # and annotate them directly and not via array_annotate
        intervals: Quantity = np.diff(channel.times)
        intervals = _quantity_concat(intervals, np.array([float("inf")]) * s)
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

############################# Extra Stimuli #############################

# gets the start:stop indices for each extra stimulus group
def _group_stimuli(channel: Event, time_threshold: Quantity) -> List[Tuple[int, int]]:
    result: List[Tuple(int, int)] = []
    last_ev: Quantity = None
    start_index: int = 0
    for i, ev in enumerate(channel.times):
        if last_ev is not None and ev - last_ev > time_threshold:
            result.append((start_index, i))
            start_index = i
        last_ev = ev
    # add the last one
    if start_index < len(channel.times):
        result.append((start_index, len(channel.times)))
    return result

def _create_extra_stimuli_channel(from_channel: Event, time_threshold: Quantity) -> Epoch:
    stimuli: List[Tuple[int, int]] = _group_stimuli(from_channel, time_threshold)
    #data_points: List[Quantity] = [from_channel.times[start:stop] for start, stop in stimuli]
    # the label of each timespan is the label of the first event
    labels = np.array([from_channel.labels[start] for start, _ in stimuli])
    # the timestamp of each timespan is the timestamp of the first event
    times: Quantity = np.array([from_channel.times[start] for start, _ in stimuli]) * from_channel.units
    # the duration is the time difference between the first and last event
    durations: Quantity = np.array([from_channel.times[stop-1] - from_channel.times[start] for start, stop in stimuli]) * from_channel.units
    frequencies: Quantity = None
    # with this deactivate the divide by 0 warning from NP
    # it just returns infinity
    with np.errstate(divide="ignore"):
        # the frequency is the number of pulses by the duration.
        # FIXME: shouldn't it be the number -1 as the last one marks exactly the end, so we only count the ones in the middle?
        frequencies = np.array([(stop - start) / durations[i] for i, (start, stop) in enumerate(stimuli)]) / from_channel.units
    frequencies.units = Hz
    epoch = Epoch(times=times, durations=durations, labels=labels, units=from_channel.units)
    epoch.array_annotate(frequencies=frequencies)
    return epoch
    

def _prepare_extra_stimuli(segment: Segment, stimuli_channels: EventChannelReferences, time_threshold: Quantity = 1*s):
    # basically the same as _prepare_stimuli
    if stimuli_channels is None:
        return
    channels = _normalize_channel_refs(stimuli_channels)
    extra_stimulus_index = 0
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
        from_channel = channel.annotations.get("forked_from", channel.name)
        marker = channel.annotations.get("marker", None)
    
        extra_stimuli_channel = _create_extra_stimuli_channel(channel, time_threshold)
        type_id = TypeID.ELECTRICAL_EXTRA_STIMULUS.value
        extra_stimuli_channel.name = f"{type_id}: {channel.name}"
        channel_id = f"{type_id}.{extra_stimulus_index}"
        extra_stimulus_index += 1
        extra_stimuli_channel.annotate(id=channel_id, type_id=type_id, from_channel=from_channel)
        if marker is not None:
            extra_stimuli_channel.annotate(marker=marker)
        segment.epochs.append(extra_stimuli_channel)

############################# Mechanical Stimuli #############################

# returns the start:stop tuples for when the amplitude is larger than the signal
def _find_spikes(channel: AnalogSignal, threshold: Quantity, signal_channel_index: int=0) -> List[Tuple[int, int]]:
    result: List[Tuple[int, int]] = []
    start_index: int = None
    assert channel.shape[1] > signal_channel_index
    for i, amp_lst in enumerate(channel):
        amp: Quantity = amp_lst[signal_channel_index]
        if start_index is None and amp >= threshold:
            start_index = i
        elif start_index is not None and amp < threshold:
            result.append((start_index, i))
            start_index = None
    return result

def _channel_index_to_time(channel: AnalogSignal, index: int) -> Quantity:
    result = channel.t_start + index * channel.sampling_period
    # ensure unit compatibility
    result.units = channel.sampling_period.units
    return result

def _spiketrain_from_raw(channel: AnalogSignal, threshold: Quantity) -> SpikeTrain:
    assert channel.signal.shape[1] == 1
    spikes = _find_spikes(channel, threshold)
    signal = channel.signal.squeeze()
    times = np.array([_channel_index_to_time(channel, start) for start, _ in spikes]) * channel.sampling_period.units
    waveforms = np.array([[signal[start:stop]] for start, stop in spikes]) * channel.units
    name = f"{channel.name}#{threshold}"
    result = SpikeTrain(name=name, times=times, units=channel.units, t_start=channel.t_start, t_stop=channel.t_stop,
                        waveforms=waveforms, sampling_rate=channel.sampling_rate, sort=True)
    result.annotate(from_channel=channel.name, threshold=threshold)
    return result

def _get_amplitudes(channel: SpikeTrain) -> Quantity:
    # there is probably a numpy version of this
    return np.array([max(wave[0]) for wave in channel.waveforms]) * channel.units

def _prepare_mechanical_stimuli(segment: Segment, from_raw: MechanicalStimulusReferences, spike_channels: SpikeChannelReferences) -> None:
    type_id = TypeID.MECHANICAL_STIMULUS.value
    stimulus_index = 0
    if from_raw is not None:
        for channel_ref, threshold in from_raw:
            # create a new spiketrain from the raw signal
            raw_channel = _channel_by_reference(segment.analogsignals, channel_ref)
            new_channel = _spiketrain_from_raw(raw_channel, threshold)
            # set id
            channel_id = f"{type_id}.{stimulus_index}"
            stimulus_index += 1
            new_channel.annotate(id=channel_id, type_id=type_id)
            new_channel.array_annotate(amplitudes=_get_amplitudes(new_channel))
            # add channel to segment
            segment.spiketrains.append(new_channel)
    if spike_channels is not None:
        spike_channels = _normalize_channel_refs(spike_channels)
        for channel_ref in spike_channels:
            # for already prepared spike channels we have nothing to do but add the id and type_id
            channel = _spiketrain_by_reference(segment.spiketrains, channel_ref)
            channel_id = f"{type_id}.{stimulus_index}"
            stimulus_index += 1
            channel.annotate(id=channel_id, type_id=type_id)
            channel.array_annotate(amplitudes=_get_amplitudes(channel))
            
############################# Action potentials #############################

def _prepare_action_potentials(segment: Segment, channel_refs: SpikeChannelReferences) -> None:
    if channel_refs is None:
        return
    ap_index = 0
    type_id = TypeID.ACTION_POTENTIAL.value
    for ap_ref in channel_refs:
        ap_channel: SpikeTrain = _spiketrain_by_reference(segment.spiketrains, ap_ref)
        assert ap_channel is not None
        # Set the id
        channel_id = f"{type_id}.{ap_index}"
        ap_index += 1
        ap_channel.annotate(type_id=type_id, id=channel_id)


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
                      extra_stimuli_event_channels: EventChannelReferences = None,
                      mechanical_stimuli_from_raw: MechanicalStimulusReferences = None,
                      mechanical_stimuli_channels: SpikeChannelReferences = None,
                      action_potential_channels: SpikeChannelReferences=None,
                      raw_channels: Set[ChannelReference] = None) -> Block:
    spikeio = Spike2IO(filename=str(file_name.resolve()))
    blocks = spikeio.read(lazy=False, load_waveforms=True)
    spike_data = blocks[0]
    for segment in spike_data.segments:
        _prepare_segment(segment)
        _prepare_raw_data(segment, raw_channels)
        _prepare_stimuli(segment, stimuli_event_channels)
        _prepare_extra_stimuli(segment, extra_stimuli_event_channels)
        _prepare_mechanical_stimuli(segment, mechanical_stimuli_from_raw, mechanical_stimuli_channels)
        _prepare_action_potentials(segment, action_potential_channels)
        _prune_segment(segment)
    return spike_data