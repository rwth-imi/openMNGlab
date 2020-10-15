# import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from math import ceil
from plotting import get_fibre_color

## Produces an interactive falling leaf plot (FLP) or waterfall plot, using plotly.
class FallingLeafPlot:
	
	## Creates the plot object with the given dimensions
	def __init__(self, width = 1000, height = 600):
		self.width = width
		self.height = height
	
	## Creates a plotly figure for the FLP.
	# @param regular_stimuli List of the regular stimulus events in the recording
	# @param action_potentials List of APs in the recording
	# @param num_intervals Number of intervals (between two regular stimuli) to be plotted. This value should not be set too high, else the plotting takes very long.
	# @param t_start Start time for plotting the FLP in seconds. E.g. 1000s plots only intervals beyond the 1000s mark.
	# @param post_stimulus_timeframe Length of the signal that should be plotted after the stimulation event. Should be kept low to increase speed.
	# @param plot_raw_signal Whether or not the raw signal from the recording should be plotted beneath the events. This is what makes the plotting slow.
	def plot(self, regular_stimuli, action_potentials, t_start, num_intervals, ap_tracks = [], post_stimulus_timeframe = float("infinity"), plot_raw_signal = True):
		# first, select the intervals according to start time and number of intervals
		regular_stimuli = [stim for stim in regular_stimuli if stim.timepoint > t_start]
		regular_stimuli = regular_stimuli[0 : num_intervals]
				
		# filter the action potentials belonging to these stimuli
		action_potentials = [ap for ap in action_potentials if ap.prev_stimuli["regular"] in regular_stimuli]
				
		# set up the figure object
		fig = go.Figure(layout = {
			"width": self.width, 
			"height": self.height, 
			"yaxis": {"autorange": "reversed", "title": "Time (s)"},
			"xaxis": {"title": "Latency (s)"}
		})
		
		with fig.batch_update():
			# build a trace for the regular stimuli
			fig.add_trace(
				go.Scatter(
					mode = "markers",
					x = [0] * len(regular_stimuli),
					y = [stim.timepoint for stim in regular_stimuli],
					marker_color = "Black",
					marker_symbol = "star",
					hovertemplate = "%{text}",
					text = ["time = " + "{:1.4f}".format(stim.timepoint) + "s<br>Index = " + str(idx) for idx, stim in enumerate(regular_stimuli)],
					name = "Electrical Stimuli"
				)
			)
			
			if plot_raw_signal == True:
				# get the max signal value that must be printed
				max_signal_value = max([max(stim.interval_raw_signal) for stim in regular_stimuli])
			
				# print the raw signal for each of the intervals
				for index, stim in enumerate(regular_stimuli):
					raw_signal = stim.interval_raw_signal
					
					# cut the raw signal snippets according to the desired timeframe after the stimulus
					t_max = min(stim.interval_length, post_stimulus_timeframe)
					last_sample = ceil(len(raw_signal) * (t_max / stim.interval_length))
					raw_signal = raw_signal[range(0, last_sample)]
					
					# check how much space we have for scaling the raw data
					if index > 0:
						timediff_prev = stim.timepoint - regular_stimuli[index - 1].timepoint
					else:
						timediff_prev = 2.0
						
					if index < len(regular_stimuli) - 1:
						timediff_next = regular_stimuli[index + 1].timepoint - stim.timepoint
					else:
						timediff_next = 2.0
						
					# then, calculate the space we have for plotting the raw values
					space_margin = .45 * min(timediff_prev, timediff_next)
					
					# scale the signal accordingly
					signal_scaling_factor = space_margin / max_signal_value
					raw_signal = [signal_scaling_factor * val + stim.timepoint for val in raw_signal]
					time_space = np.linspace(0, t_max, len(raw_signal))
					
					# plot the signal using linspace for the time
					fig.add_trace(
						go.Scatter(
							mode = "lines",
							x = time_space,
							y = raw_signal,
							line = {
								"color": 'firebrick', 
								"width": .5
							},
							hovertemplate = "%{text}",
							text = ["time = " + "{:1.4f}".format(t) + "s<br>amp = " + "{:1.2f}".format(s) + "mV" for t, s in zip(time_space, raw_signal)],
							legendgroup = "rawsignal",
							name = "Raw Signal",
							showlegend = True if index == 0 else False
						)
					)
			else:
				# TODO simply print a line instead of the signal
				pass
				
			# Finally, print markers for the action potentials
			for actpot in action_potentials:
				# check if this lies in the post stimulus timeframe that should be displayed
				if actpot.features["latency"] > post_stimulus_timeframe:
					continue
			
				# get previous stimulus and its timestamp
				prev_stimulus = actpot.prev_stimuli["regular"]
				prev_timept = prev_stimulus.timepoint
				
				fig.add_trace(
					go.Scatter(
						mode = "markers",
						x = [actpot.features["latency"], actpot.features["latency"] + actpot.duration],
						y = [prev_timept] * 2,
						marker_symbol = ["triangle-nw", "triangle-ne"],
						marker_size = 7,
						marker_color = get_fibre_color(actpot.implied_fibre_index) if actpot.implied_fibre_index != None else "black",
						hovertemplate = "%{text}",
						text = ["Latency: " + "{:1.4f}".format(actpot.features["latency"]) + "s<br>" + "Fibre Index: " + str(actpot.implied_fibre_index), \
						"Offset: " + "{:1.4f}".format(actpot.features["latency"] + actpot.duration) + "s"],
						showlegend = False
					)
				)
			
			# plot the AP tracks
			for ap_track in ap_tracks:
				fig.add_trace(
					go.Scatter(
						mode = "lines",
						x = [latency for latency in ap_track.latencies],
						y = [regular_stimuli[sweep_idx].timepoint for sweep_idx in ap_track.sweep_idcs],
						line = {
							"color": 'red',
							"width": .75
						},
						name = "AP Track"
					)
				)
			
		fig.show()
		
		self.fig = fig