from typing import List
from importers.mng_importer import MNGImporter
from neo.core import AnalogSignal, Segment, SpikeTrain
from signal_artifacts import ActionPotential, ElectricalStimulus, MechanicalStimulus

from numpy import ndarray
from math import floor, ceil

## The interface for a general MNG importer.
class NeoImporter(MNGImporter):
    neo_data: Segment
    analog_signal_channel: AnalogSignal

    def __init__(self, neo_data: Segment, analog_signal_channel_name: str):
        self.neo_data = neo_data
        self.analog_signal_channel = find_channel_by_name(analog_signal_channel_name)
        assert self.analog_signal_channel is not None
   
    ## Returns the raw signal values from the recording
    def get_raw_signal(self) -> ndarray:
        # Unlike the super class MNGImporter we don't return a List of floats,
        # because this would require copieng all data points, which would just be slightly faster
        # than the full decomposition of a dead cats body **hint** thats quite slow **/hint**
        # Hopefully pythons type magic makes this work seamless

        # An AnalogSignal is basically nothing but a fancy numpy array
        return self.analog_signal_channel
      
    ## Returns the raw signal, but split by the regular electrical stimuli
    def get_raw_signal_split_by_stimuli(self, stimuli: List[ElectricalStimulus]) -> List[ndarray]:
        # Signature change has the same reasoning as above
        result = []
        interval_start = 0
        for stimulus in stimuli:
            interval_stop = compute_time_index(self.analog_signal_channel, stimulus.timepoint) + 1
            interval = self.analog_signal_channel[interval_start:interval_stop]
            result.append(interval)
            interval_start = interval_stop
        if interval_start < len(self.analog_signal_channel):
            result.append(self.analog_signal_channel[interval_start:])

        return result

    ## Returns a list of all action potentials in the recording
    def get_action_potentials(self, ap_channel_name: str) -> List[ActionPotential]:
        ap_channel = find_channel_by_name(self.neo_data.spiketrains, ap_channel_name)
        assert ap_channel is not None
        assert hasattr(ap_channel, "waveforms")

        result = []
        for spike_id, spike_start in enumerate(ap_channel.times):
            # 2nd index is the channel, neo supports multiple channel
            # TBH I have no idea what that even means
            spike_data = ap_channel.waveforms[spike_id, 0, :]
            spike_duration = len(spike_data) * ap_channel.sampling_period
            spike_stop = spike_start + spike_duration
            ap = ActionPotential(spike_start, spike_stop, spike_data)
            result.append(ap)
        
        return result
   
    def __complete_electrical_stimulus(self, stim, end_time):
        interval_start = compute_time_index(self.analog_signal_channel, stim.timepoint)
        interval_stop = compute_time_index(self.analog_signal_channel, end_time) + 1
        stim.interval_length = end_time - stim.timepoint
        stim.interval_raw_signal = self.analog_signal_channel[interval_start:interval_stop]
       

    ## Returns a list of all the regular electrical stimuli in the recording
    def get_electrical_stimuli(self, stimulus_channel_name) -> List[ElectricalStimulus]:
        stimulus_channel = find_channel_by_name(self.neo_data.events, stimulus_channel_name)
        assert stimulus_channel is not None

        result = []
        for stimulus_time in stimulus_channel:
            if len(result) > 0:
                self.__complete_electrical_stimulus(result[-1], stimulus_time)
            result.append(ElectricalStimulus(stimulus_time))
        if len(result) > 0:
            self.__complete_electrical_stimulus(result[-1], AnalogSignal.t_stop)
        
        return result

    ## If present in the format, an importer can implement this function to return all burst of "extra stimuli"
    def get_extra_stimuli(self):
        # I have no idea what this is supposed to be
        pass
        
    ## If needed, use this function to return/retrieve mechanical stimulation of the C-fibres
    def get_mechanical_stimuli(self, force_channel, threshold, max_gap_time) -> List[MechanicalStimulus]:
        force_channel = find_channel_by_name(self.neo_data.analogsignals)
        assert force_channel is not None

        result = []
        for i, datapoint in enumerate(force_channel):
            if datapoint < threshold:
                continue
            datapoint_at = compute_index_time(force_channel, i)
            datapoint_after = compute_index_time(force_channel, i + 1)
            # if we are still in the range of the last stimulus we just update it
            if len(result) > 0 and result[-1].offset + max_gap_time >= datapoint_after:
                result[-1].offset = datapoint_after
                if datapoint > result[-1].amplitude:
                    result[-1].amplitude = datapoint
            else:
                # otherwise we create a new one
                result.append(MechanicalStimulus(datapoint_at, datapoint_after, [datapoint]))

        return result



def find_channel_by_name(channels, name) -> AnalogSignal:
    for c in channels:
        if c.name == name:
            return c
    return None

def compute_time_index(channel: AnalogSignal, at_time) -> int:
    # Simple linear translation
    from_start = at_time - channel.t_start
    return from_start // channel.sampling_period

def compute_index_time(channel: AnalogSignal, at_index):
    return channel.t_start + (at_index * channel.sampling_period)
