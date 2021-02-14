# import matplotlib.pyplot as plt
# from fibre_tracking.ap_track import APTrack
from typing import Iterable, Union
from neo.core.spiketrain import SpikeTrain
import numpy as np
import plotly.graph_objects as go
from math import floor, ceil

from quantities.quantity import Quantity
from plotting import get_fibre_color
from neo_importers.neo_wrapper import ChannelWrapper, ElectricalStimulusWrapper, ActionPotentialWrapper, MNGRecording
from fibre_tracking.ap_track import APTrack
from features import FeatureDatabase
from neo.core import AnalogSignal
from quantities import second

## Produces an interactive falling leaf plot (FLP) or waterfall plot, using plotly.
class FallingLeafPlot:
	
	## Creates the plot object with the given dimensions and recording
	def __init__(self, recording: MNGRecording, feature_db: FeatureDatabase, width = 1000, height = 600):
		self.recording = recording
		self.feature_db = feature_db
		self.width = width
		self.height = height
	
	## Creates a plotly figure for the FLP.
	# @param regular_stimuli List of the regular stimulus events in the recording
	# @param action_potentials List of APs in the recording
	# @param num_intervals Number of intervals (between two regular stimuli) to be plotted. This value should not be set too high, else the plotting takes very long.
	# @param t_start Start time for plotting the FLP in seconds. E.g. 1000s plots only intervals beyond the 1000s mark.
	# @param post_stimulus_timeframe Length of the signal that should be plotted after the stimulation event. Should be kept low to increase speed.
	# @param plot_raw_signal Whether or not the raw signal from the recording should be plotted beneath the events. This is what makes the plotting slow.
	def plot(self, el_stimuli_channel: str = "es.0", action_potential_channels: Union[str, Iterable[str]] = "all", analog_signal_channel: str = "rd.0", \
			t_start: float = 0 * second, num_intervals: int = 10, ap_tracks: Iterable = [], \
			post_stimulus_timeframe: float = float("infinity") * second, plot_raw_signal: bool = False):
		
		# first, select the intervals according to start time and number of intervals
		el_stimuli = list(self.recording.electrical_stimulus_channels[el_stimuli_channel]) 
		el_stimuli = sorted(el_stimuli, key = lambda st: st.time)
		disp_el_stimuli = [st for st in el_stimuli if st.time > t_start]
		disp_el_stimuli = np.array(disp_el_stimuli[0 : num_intervals])

		# calculate the max. time that we need to display
		last_stimulus_idx = np.argmax([st.time for st in disp_el_stimuli])
		t_max = disp_el_stimuli[last_stimulus_idx].time + disp_el_stimuli[last_stimulus_idx].interval

		# set up the figure object
		fig = go.Figure(layout = {
			"width": self.width, 
			"height": self.height, 
			"yaxis": {"autorange": "reversed", "title": "Time (s)"},
			"xaxis": {"title": "Latency (" + str(post_stimulus_timeframe.dimensionality) + ")"}
		})
		
		with fig.batch_update():
			# build a trace for the regular stimuli
			fig.add_trace(
				go.Scattergl(
					mode = "markers",
					x = np.zeros(len(disp_el_stimuli)),
					y = np.array([stim.time for stim in disp_el_stimuli]),
					marker_color = "Black",
					marker_symbol = "star",
					hovertemplate = "%{text}",
					text = ["time = " + "{:1.4f}".format(stim.time) + "<br>Index = " + str(stim.index) for stim in disp_el_stimuli],
					name = "Electrical Stimuli"
				)
			)

			if plot_raw_signal == True:
				# retrieve and restrict to our time range
				raw_signal: AnalogSignal = self.recording.raw_data_channels[analog_signal_channel]
				# start_idx = max(0, floor(t_start * raw_signal.sampling_rate))
				# stop_idx = min(len(raw_signal), ceil(t_max * raw_signal.sampling_rate))
				# raw_signal = raw_signal[start_idx : stop_idx]
				# TODO check if flattening the signal is always a good idea here
				raw_signal = raw_signal.flatten()

				# get the max signal value that must be printed
				max_signal_value = np.max(raw_signal)
			
				stim: ElectricalStimulusWrapper
				# print the raw signal for each of the intervals
				for index, stim in enumerate(disp_el_stimuli):
					# cut the raw signal snippets according to the desired timeframe after the stimulus
					sweep_disp_duration = min(stim.interval, post_stimulus_timeframe)
					sweep_first_idx = max(0, floor(raw_signal.sampling_rate * stim.time))
					sweep_last_idx = min(len(raw_signal), ceil(raw_signal.sampling_rate * (stim.time + sweep_disp_duration)))
					sweep_raw_signal = raw_signal[sweep_first_idx : sweep_last_idx]
					
					# check how much space we have for scaling the raw data
					if index > 0:
						timediff_prev = stim.time - disp_el_stimuli[index - 1].time
					else:
						timediff_prev = 2.0
					if index < len(disp_el_stimuli) - 1:
						timediff_next = disp_el_stimuli[index + 1].time - stim.time
					else:
						timediff_next = 2.0
						
					# then, calculate the space we have for plotting the raw values
					space_margin = .45 * min(timediff_prev, timediff_next)
					
					# scale the signal accordingly
					signal_scaling_factor: Quantity = space_margin / max_signal_value
					time_space = np.linspace(0 * second, sweep_disp_duration, len(sweep_raw_signal))

					# plot the signal using linspace for the time
					fig.add_trace(
						go.Scattergl(
							mode = "lines",
							x = time_space,
							y = signal_scaling_factor.magnitude * sweep_raw_signal.magnitude + stim.time.magnitude,
							line = {
								"color": 'firebrick', 
								"width": .5
							},
							hovertemplate = "%{text}",
							text = ["time = " + "{:1.4f}".format(t) + "<br>amp = " + "{:1.2f}".format(s) for t, s in zip(time_space + stim.time, sweep_raw_signal)],
							legendgroup = "rawsignal",
							name = "Raw Signal",
							showlegend = True if index == 0 else False
						)
					)
			else:
				# TODO simply print a line instead of the signal
				pass

			# process the ap channel parameter
			if isinstance(action_potential_channels, str):
				if action_potential_channels == "all": # replace by list with all channels
					action_potential_channels = list(self.recording.action_potential_channels.keys())
				else: # wrap in a list
					action_potential_channels = [action_potential_channels]

			# Finally, print markers for the action potentials
			# we do this individually for each channel
			channel_wrapper: ChannelWrapper
			ap_channel: SpikeTrain
			for channel_name, channel_wrapper in self.recording.action_potential_channels.items():
				# skip if this channel should not be displayed
				if channel_name not in action_potential_channels:
					continue
				# otherwise, get info about the APs
				ap_channel = channel_wrapper.channel
				ap_indices = np.where((ap_channel.times >= t_start) & (ap_channel.times <= t_max))
				ap_times = ap_channel.times[ap_indices]
				# calculate durations of APs from their waveforms
				ap_durations: Quantity = np.array([ap.size for ap in ap_channel.waveforms[ap_indices]]) / ap_channel.sampling_rate
				ap_durations = ap_durations.magnitude * second
				
				assert len(ap_times) == len(ap_durations)

				aps_x = []
				aps_y = []
				stim: ElectricalStimulusWrapper
				for stim in disp_el_stimuli:
					# check if the action potentials are within the display range,
					# i.e. lie before the end of the interval
					aps_in_display_range = (ap_times >= stim.time) & (ap_times <= stim.time + min(stim.interval, post_stimulus_timeframe))
					# calculate their x- and y-coordinates
					start_times = ap_times[aps_in_display_range] - stim.time
					stop_times = ap_times[aps_in_display_range] + ap_durations[aps_in_display_range] - stim.time
					# add new points to the list of x- and y-coordinates
					for t_onset, t_offset in zip(start_times, stop_times):
						aps_x += [t_onset, t_offset]
					aps_y += [stim.time] * 2 * sum(aps_in_display_range)
					
					assert len(aps_x) == len(aps_y)
				
				# plot the APs using these coordinates
				fig.add_trace(
					go.Scatter(
						mode = "markers",
						x = aps_x,
						y = aps_y,
						marker_symbol = ["triangle-nw", "triangle-ne"] * ceil(len(aps_x) / 2),
						marker_size = 7,
						# marker_color = "black",
						hovertemplate = "%{text}",
						text = ["Latency: " + "{:1.4f}".format(latency) for latency in aps_x],
						name = channel_name,
						showlegend = True
					)
				)
		
			# TODO Plot AP tracks only if they actually are in display range
			# plot the AP tracks
			ap_track: APTrack
			for ap_track in ap_tracks:

				# filter only those sweeps from the track which are actually displayed
				track_y = []
				track_x = []
				for stim_idx, latency in zip(ap_track.sweep_idcs, ap_track.latencies):
					if el_stimuli[stim_idx].time > t_start and el_stimuli[stim_idx].time < t_max:
						track_y.append(el_stimuli[stim_idx].time)
						track_x.append(latency)

				# print(track_x)
				# print(track_y)
				print(t_start, t_max)

				# if the track is not within the display range, we can skip this altogether
				if len(track_x) == 0 and len(track_y) == 0:
					continue
				else:
					fig.add_trace(
						go.Scatter(
							mode = "lines",
							x = track_x,
							y = track_y,
							line = {
								"color": ap_track.color,
								"width": .75
							},
							name = ap_track.name
						)
					)
		
		fig.show()
		
		self.fig = fig