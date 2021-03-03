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
from neo_importers.neo_utils import store_original_names, make_names_unique, quantity_concat, \
                                    remove_array_annotations, remove_empty_names, prune_segment, \
                                    find_spikes, channel_index_to_time, spiketrain_from_raw, spike_amplitudes

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

## Normalizes channel references for event channels
#  Event channels are referenced by channelreference - marker tuples, which, for the ease of writing can
#  be written as a dict { ref: marker }, or as a set of tuples. This function converts the dict to the set variant
# @param references either set of tuples, or a dict of the form {ref: marker}
# @returns A set of tuples for channel references
def _normalize_channel_refs(references: EventChannelReferences) -> Set[EventChannelReference]:
    if isinstance(references, set):
        return references
    result: Set[EventChannelReference] = set()
    for ch_ref, items in references.items():
        result.update([(ch_ref, item) for item in items])
    return result

## Returns the channel that is referenced by either the spike2 channel ID or by the channel name
#  @param channels Iterable container containing all channels
#  @param ref channel reference, either the channel name (str) or the spike2 channel ID (int)
#  @returns The first channel in the container matching the reference
def _channel_by_reference(channels: Iterable[DataObject], ref: ChannelReference) -> DataObject:
    for channel in channels:
        if (isinstance(ref, str) and channel.name == ref) \
            or (isinstance(ref, int) and channel.annotations.get("channel_id", None) == ref):
            return channel
    return None

## Returns a spike train channel referenced by the channel name or spike2 channel ID, as well as the filter
#  @param channels Iterable container containing all channels
#  @param tuple of a channel reference, either the channel name (str) or the spike2 channel ID (int), and the filter index
#  @returns The first channel in the container matching the reference
def _spiketrain_by_reference(channels: Iterable[SpikeTrain], ref: SpikeChannelReference) -> SpikeTrain:
    if isinstance(ref, str) or isinstance(ref, int):
        return _channel_by_reference(channels, ref)
    ch_ref, spike_filter = ref
    for channel in channels:
        if (isinstance(ch_ref, str) and channel.name == f"{ch_ref}#{spike_filter}") \
            or (isinstance(ch_ref, int) and channel.annotations.get("channel_id", None) == ch_ref \
                and channel.annotations.get("spike_filter", None) == spike_filter):
            return channel

## Returns a event channel referenced by the channel name or spike2 channel ID, and optionally also the marker
#  @param channels Iterable container containing all channels
#  @param channel reference, either the channel name (str) or the spike2 channel ID (int), or a tuple of the channel reference and the marker (str)
#  @returns The first channel in the container matching the reference
def _event_channel_by_reference(channels: Iterable[Event], ref: EventChannelReference) -> Event:
    if isinstance(ref, str) or isinstance(ref, int):
        return _channel_by_reference(channels, ref)
    ch_ref, marker = ref
    for channel in channels:
        if (isinstance(ch_ref, str) and channel.name == f"{ch_ref}#{marker}") \
            or (isinstance(ch_ref, int) and channel.annotations.get("channel_id", None) == ch_ref \
                and channel.annotations.get("marker", None) == marker):
            return channel

############################# Spiketrains #############################

## Takes a list of spiketrains and groups them by the channel they reference
#  Used to distinguish channels with the same name
#  @param spiketrains list of all all spiketrains
#  @returns a Dict mapping all spiketrains belonging to the same channel to that channel id
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

## Make channel names unique for channels with the same name, by adding an index to the name
#  @param spiketrain_channels List of a List of all spiketrains per channel with the same name
def _make_spiketrain_names_unique_per_channel(spiketrain_channels: List[List[SpikeTrain]]) -> None:
    if len(spiketrain_channels) == 1:
        return
    for i, spiketrains in enumerate(spiketrain_channels):
        for spiketrain in spiketrains:
            spiketrain.name = f"{spiketrain.name}_{i}"

## Make names of spiketrains of the same channel with different filters unique by adding the filter index to the name
#  @param spiketrains the list of spiketrains
def _make_spiketrain_names_unique_per_marker(spiketrains: List[SpikeTrain]) -> None:
    for spiketrain in spiketrains:
        spiketrain.name = f"{spiketrain.name}#{spiketrain.annotations['spike_filter']}"

## Prepares spiketrain channels for later use. This includes unifying the reference format (ids, channel names)
# @param segment the Neo segment of which the spiketrains shall be prepared
def _prepare_spiketrains(segment: Segment) -> None:
    # lists of all spiketrains with the same name
    channels: Dict[str, List[SpikeTrain]] = {st.name: [s for s in segment.spiketrains if s.name == st.name] for st in segment.spiketrains}
    for spiketrains in channels.values():
        channel_refs = _group_spiketrains_by_channel_ref(spiketrains)
        _make_spiketrain_names_unique_per_channel(channel_refs.values())
        _make_spiketrain_names_unique_per_marker(spiketrains)

############################# Events #############################

## Store the spike2 channel id in the annotations as channel_id
#  this ensures a unified referencing scheme over all channel types
#  @param events List containing all event channels
def _assign_event_channel_ids(events: List[Event]) -> None:
    for event in events:
        event.annotate(channel_id=event.annotations["id"])

## Prepares event channels for later use. This includes unifying the reference format (ids, channel names)
# @param segment the Neo segment of which the spiketrains shall be prepared
def _prepare_events(segment: Segment) -> None:
    events: List[Event] = segment.events
    make_names_unique(events)
    _assign_event_channel_ids(events)

############################# Semantic datastructures #############################

############################# Electrical stimuli #############################

## Creates a new event channel from an existing one, containing only labels that satisfy a condition
#  @param event_channel Event channel to be forked from
#  @param label_filter function that evaluates if a datapoint should be included in the result
#  @result Event channel without a name, that only contains datapoints for which label_filter evaluated to true
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

## Creates a new event channel from another channel only containing datapoints where the marker matches a predefined value
#  @param segment the segment to add the channel to
#  @param channel_ref the reference to the channel that should be forked
#  @param marker the marker for which to filter the channel
#  @returns a newly created event channel with a unique name that contains all datapoints from the referenced channel that have the given marker label 
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

## Converts stimuli event channels into the unified format for later use.
#  This includes splitting event channels containing multiple different markers into separate channels
#  and also adding required meta information to the annotations. 
#  These annotations are:
#  * id: the unified channel id of our format
#  * type_id: the id of the type of channel (ELECTRICAL_STIMULUS)
#  * intervals: array of intervals from each event to the next, last one is infinite (as there is no next event)
#  @param segment the Neo segment containing the event channels
#  @param stimuli_channels references (either channel name or name - marker pairs) of the event channels of interest
#  @returns a dict mapping channel names to our unified id format
def _prepare_stimuli(segment: Segment, stimuli_channels: EventChannelReferences) -> Dict[str, str]:
    if stimuli_channels is None:
        return {}
    channels = _normalize_channel_refs(stimuli_channels)
    stimulus_index = 0
    result = {}
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
        intervals = quantity_concat(intervals, np.array([float("inf")]) * s)
        channel.array_annotate(intervals=intervals)
        result[channel.name] = channel_id
    return result

############################# Raw data #############################

## Converts raw data channels to our unified format for later use
#  This means adding the required meta information:
#  * id: the unified channel id of our format
#  * type_id: the id of the type of channel (RAW_DATA)
#  @param segment the Neo segment containing the signal channels
#  @param raw_channels references (name or id) of the signal channels of interest
#  @returns a dict mapping channel names to our unified id format
def _prepare_raw_data(segment: Segment, raw_channels: Set[ChannelReference]) -> Dict[str, str]:
    if raw_channels is None:
        raw_channels = {a.name for a in segment.analogsignals}
    result = {}
    index = 0
    type_id = TypeID.RAW_DATA.value
    for channel_ref in raw_channels:
        channel = _channel_by_reference(segment.analogsignals, channel_ref)
        channel_id = f"{type_id}.{index}"
        index += 1
        channel.annotate(id=channel_id, type_id=type_id)
        result[channel.name] = channel_id
    return result

############################# Extra Stimuli #############################

## Groups stimuli that are at most a certain interval apart together
#  @param channel event channel containing the stimuli
#  @param time_threshold maximum time between stimuli (as quantity convertable to time)
#  @returns a List [start:stop] of the stimuli indices per group
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

## Creates new extra stimuli channel from event channelm where each extra stimuli is the time interval of stimuli groups
#  @param from_channel the event channel containing the extra stimuli groups
#  @param time_threshold maximum time between stimuli (as quantity convertable to time) so they are part of the same interval
#  @returns an epoch channel containing the intervals of each extra stimulus
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
    

## Creates extra stimulus epoch channels in the unified format for later use.
#  This creates new epoch channels from event channels in a given time threshold and annotates them with meta information
#  These annotations are:
#  * id: the unified channel id of our format
#  * type_id: the id of the type of channel (ELECTRICAL_EXTRA_STIMULUS)
#  * frequencies: array of the extra stimulus frequency for each of the stimulus intervals
#  @param segment the Neo segment containing the event channels
#  @param stimuli_channels references (either channel name or name - marker pairs) of the event channels of interest
#  @returns a dict mapping channel names to our unified id format
def _prepare_extra_stimuli(segment: Segment, stimuli_channels: EventChannelReferences, time_threshold: Quantity = 1*s) -> Dict[str, str]:
    # basically the same as _prepare_stimuli
    if stimuli_channels is None:
        return {}
    result = {}
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
        result[channel.name] = channel_id
    return result

############################# Mechanical Stimuli #############################

## Creates mechanical stimulus epoch channels in the unified format for later use.
#  This prepares existing channels or creates new ones from raw signals exceeding a certain threshold.
#  The channels are annotated with meta information:
#  * id: the unified channel id of our format
#  * type_id: the id of the type of channel (ELECTRICAL_EXTRA_STIMULUS)
#  * amplitudes: array of the maximum amplitude of each of the stimuli
#  @param segment the Neo segment containing the spiketrain and signal channels
#  @param from_raw Set of tuples of raw channel references with thresholds to extract spikes from
#  @param spike_channels references (channel reference - filter id) to spiketrains that should be prepared as mechanical stimuli
#  @returns a dict mapping channel names to our unified id format
def _prepare_mechanical_stimuli(segment: Segment, from_raw: MechanicalStimulusReferences, spike_channels: SpikeChannelReferences) -> Dict[str, str]:
    type_id = TypeID.MECHANICAL_STIMULUS.value
    result = {}
    stimulus_index = 0
    if from_raw is not None:
        for channel_ref, threshold in from_raw:
            # create a new spiketrain from the raw signal
            raw_channel = _channel_by_reference(segment.analogsignals, channel_ref)
            new_channel = spiketrain_from_raw(raw_channel, threshold)
            # set id
            channel_id = f"{type_id}.{stimulus_index}"
            stimulus_index += 1
            new_channel.annotate(id=channel_id, type_id=type_id)
            new_channel.array_annotate(amplitudes=spike_amplitudes(new_channel))
            # add channel to segment
            segment.spiketrains.append(new_channel)
            result[new_channel.name] = channel_id
    if spike_channels is not None:
        spike_channels = _normalize_channel_refs(spike_channels)
        for channel_ref in spike_channels:
            # for already prepared spike channels we have nothing to do but add the id and type_id
            channel = _spiketrain_by_reference(segment.spiketrains, channel_ref)
            channel_id = f"{type_id}.{stimulus_index}"
            stimulus_index += 1
            channel.annotate(id=channel_id, type_id=type_id)
            channel.array_annotate(amplitudes=_get_amplitudes(channel))
            result[channel.name] = channel_id
    return result
            
############################# Action potentials #############################

## Converts spiketrain channels to our unified format for later use
#  This means adding the required meta information:
#  * id: the unified channel id of our format
#  * type_id: the id of the type of channel (RAW_DATA)
#  @param segment the Neo segment containing the signal channels
#  @param channel_refs spiketrain channel references tuple of channel refrence (name or id) and filter id of the spiketrains of interest
#  @returns a dict mapping channel names to our unified id format
def _prepare_action_potentials(segment: Segment, channel_refs: SpikeChannelReferences) -> Dict[str, str]:
    if channel_refs is None:
        return
    elif isinstance(channel_refs, str):
        # load all channels if requested
        if channel_refs.lower() == "all":
            channel_refs = [st.name for st in segment.spiketrains]
        
    ap_index = 0
    type_id = TypeID.ACTION_POTENTIAL.value
    result = {}

    for ap_ref in channel_refs:
        ap_channel: SpikeTrain = _spiketrain_by_reference(segment.spiketrains, ap_ref)
        assert ap_channel is not None
        # Set the id
        channel_id = f"{type_id}.{ap_index}"
        ap_index += 1
        ap_channel.annotate(type_id=type_id, id=channel_id)
        result[ap_channel.name] = channel_id
    return result

############################# Loading #############################

## Prepare the segment for data extraction. Mainly unify name format and make them unique
#  @param segment the semgent to prepare
def _prepare_segment(segment: Segment) -> None:
    # the neo spike importer creates some faulty array annotations
    # we need to remove them because they cause errors with the NIX exporter
    remove_array_annotations(segment.data_children)
    remove_empty_names(segment.data_children)
    store_original_names(segment.data_children)
    _prepare_spiketrains(segment)
    _prepare_events(segment)

## Import a spike2 binary file into our unified format
#  @param stimuli_event_channels references to stimuli channels.
#         A reference is either a channel reference or a tuple of channel reference and marker if the channel contains multiple markers.
#         For ease of writing, also a dict { channel reference: marker } can be used
#         A channel reference is either the channel name (after being made unique) or the spike channel ID (channel number - 1)
#  @param extra_stimuli_event_channels references to extra stimuli channels.
#         A reference is either a channel reference or a tuple of channel reference and marker if the channel contains multiple markers.
#         For ease of writing, also a dict { channel reference: marker } can be used
#         A channel reference is either the channel name (after being made unique) or the spike channel ID (channel number - 1)
#  @param mechanical_stimuli_from_raw references the raw channels and the threshold to extract mechanical stimuli from. 
#         The format is a set/list of tuples of the raw channel reference and the threshold as quantity convertable to the unit of the channel
#         A channel reference is either the channel name (after being made unique) or the spike channel ID (channel number - 1)
#  @param mechanical_stimuli_channels references to already extracted spiketrain channels that represent mechanical stimuli.
#         The format is a set/list of tuples of channel references and the filter index
#         A channel reference is either the channel name (after being made unique) or the spike channel ID (channel number - 1)
#  @param action_potential_channels references the spiketrains containing the action potentials
#         The format is a set/list of tuples of channel references and the filter index
#         A channel reference is either the channel name (after being made unique) or the spike channel ID (channel number - 1)
#  @param raw_channels references to the raw signal channels as set/list
#         A channel reference is either the channel name (after being made unique) or the spike channel ID (channel number - 1)
#  @returns the Neo Block imported from spike together with a dict mapping type ids to a dict mapping channel names to the unified id format
#           The type id is the string value of the TypeID enum and the unified id format is type_id.id where id is an incrementing number unique per type_id
def import_spike_file(file_name: Path,
                      stimuli_event_channels: EventChannelReferences = None,
                      extra_stimuli_event_channels: EventChannelReferences = None,
                      mechanical_stimuli_from_raw: MechanicalStimulusReferences = None,
                      mechanical_stimuli_channels: SpikeChannelReferences = None,
                      action_potential_channels: SpikeChannelReferences=None,
                      raw_channels: Set[ChannelReference] = None) -> Tuple[Block, Dict[TypeID, Dict[str, str]]]:
    spikeio = Spike2IO(filename=str(file_name.resolve()))
    blocks = spikeio.read(lazy=False, load_waveforms=True)
    spike_data = blocks[0]
    channel_id_map = { type_id: {} for type_id in TypeID }
    for segment in spike_data.segments:
        _prepare_segment(segment)
        raw_id_map = _prepare_raw_data(segment, raw_channels)
        stimuli_id_map = _prepare_stimuli(segment, stimuli_event_channels)
        extra_stimuli_id_map = _prepare_extra_stimuli(segment, extra_stimuli_event_channels)
        mechanical_stimuli_id_map = _prepare_mechanical_stimuli(segment, mechanical_stimuli_from_raw, mechanical_stimuli_channels)
        ap_id_map = _prepare_action_potentials(segment, action_potential_channels)
        prune_segment(segment)
        channel_id_map[TypeID.RAW_DATA].update(raw_id_map)
        channel_id_map[TypeID.ELECTRICAL_STIMULUS].update(stimuli_id_map)
        channel_id_map[TypeID.ELECTRICAL_EXTRA_STIMULUS].update(extra_stimuli_id_map)
        channel_id_map[TypeID.MECHANICAL_STIMULUS].update(mechanical_stimuli_id_map)
        channel_id_map[TypeID.ACTION_POTENTIAL].update(ap_id_map)
    return spike_data, channel_id_map