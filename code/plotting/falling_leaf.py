# import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from math import ceil
from plotting import get_fibre_color

'''
	**********************************
	Produces a falling leaf plot
	**********************************
'''
class FallingLeafPlot:
	
	def __init__(self, width = 1000, height = 600):
		self.width = width
		self.height = height
	
	def plot(self, regular_stimuli, action_potentials, t_start, num_intervals, post_stimulus_timeframe = float("infinity"), plot_raw_signal = True):
		# first, select the intervals according to start time and number of intervals
		regular_stimuli = [stim for stim in regular_stimuli if stim.get_timepoint() > t_start]
		regular_stimuli = regular_stimuli[0:num_intervals]
				
		# filter the action potentials belonging to these stimuli
		action_potentials = [ap for ap in action_potentials if ap.get_prev_reg_el_stimulus() in regular_stimuli]
				
				
		# set up the figure object
		fig = go.Figure(layout = {
			"width": self.width, 
			"height": self.height, 
			"yaxis": {"autorange": "reversed", "title": "Time (s)"},
			"xaxis": {"title": "Latency (s)"}
		})
		
		# build a trace for the regular stimuli
		fig.add_trace(
			go.Scatter(
				mode = "markers",
				x = [0] * len(regular_stimuli),
				y = [stim.get_timepoint() for stim in regular_stimuli],
				marker_color = "Black",
				marker_symbol = "star",
				hovertemplate = "Electrical Stimulus:<br>at %{y}s"
			)
		)
		
		if plot_raw_signal == True:
			# get the max signal value that must be printed
			max_signal_value = max([max(stim.get_interval_raw_signal()) for stim in regular_stimuli])
		
			# print the raw signal for each of the intervals
			for index, stim in enumerate(regular_stimuli):
				raw_signal = stim.get_interval_raw_signal()
				
				# cut the raw signal snippets according to the desired timeframe after the stimulus
				t_max = min(stim.get_interval_length(), post_stimulus_timeframe)
				last_sample = ceil(len(raw_signal) * (t_max / stim.get_interval_length()))
				raw_signal = raw_signal[range(0, last_sample)]
				
				# check how much space we have for scaling the raw data
				if index > 0:
					timediff_prev = stim.get_timepoint() - regular_stimuli[index - 1].get_timepoint()
				else:
					timediff_prev = 2.0
					
				if index < len(regular_stimuli) - 1:
					timediff_next = regular_stimuli[index + 1].get_timepoint() - stim.get_timepoint()
				else:
					timediff_next = 2.0
					
				# then, calculate the space we have for plotting the raw values
				space_margin = .45 * min(timediff_prev, timediff_next)
				
				# scale the signal accordingly
				signal_scaling_factor = space_margin / max_signal_value
				raw_signal = [signal_scaling_factor * val + stim.get_timepoint() for val in raw_signal]
				
				# plot the signal using linspace for the time
				fig.add_trace(
					go.Scatter(
						mode = "lines",
						x = np.linspace(0, t_max, len(raw_signal)),
						y = raw_signal,
						line = {
							"color": 'firebrick', 
							"width": .5
						},
						hovertemplate = "Raw signal<br>%{x}s<br>%{y}mV"
					)
				)
		else:
			# TODO simply print a line instead of the signal
			pass
			
		# Finally, print markers for the action potentials
		for actpot in action_potentials:
			# check if this lies in the post stimulus timeframe that should be displayed
			if actpot.get_dist_to_prev_reg_el_stimulus() > post_stimulus_timeframe:
				continue
		
			# get previous stimulus and its timestamp
			prev_stimulus = actpot.get_prev_reg_el_stimulus()
			prev_timept = prev_stimulus.get_timepoint()
			
			fig.add_trace(
				go.Scatter(
					mode = "markers",
					x = [actpot.get_dist_to_prev_reg_el_stimulus(), actpot.get_dist_to_prev_reg_el_stimulus() + actpot.get_duration()],
					y = [prev_timept] * 2,
					marker_symbol = ["triangle-nw", "triangle-ne"],
					marker_size = 7,
					marker_color = get_fibre_color(actpot.get_implied_fibre_index()),
					hovertemplate = "%{text}",
					text = ["Latency: " + "{:1.4f}".format(actpot.get_dist_to_prev_reg_el_stimulus()) + "s<br>" + "Fibre Index: " + str(actpot.get_implied_fibre_index()), \
					"Offset: " + "{:1.4f}".format(actpot.get_dist_to_prev_reg_el_stimulus() + actpot.get_duration()) + "s"]
				)
			)
			
		
			
		fig.show()
		
		self.fig = fig
			
	'''
	def plot(self, regular_stimuli, action_potentials, plot_hlines = True, plot_raw_signal = False, max_signal_value = 500, time_start = 0, time_stop = float("infinity"), post_stimulus_timeframe = 0.05):
		fig = plt.figure(figsize = (self.width, self.height))
	
		# plot the regular stimuli for reference
		for index, regstim in enumerate(regular_stimuli):
			timept = regstim.get_timepoint()
			
			# check, if this is in the timerange that we want
			if timept > time_start and timept < time_stop:
				plt.scatter(x = 0, y = regstim.get_timepoint(), marker = "*", color = "k")
			
				# plot horizontal helper lines
				if plot_hlines == True:
					plt.gca().axhline(y = regstim.get_timepoint(), color = "g", linewidth = ".5")
					
				# plot raw signal
				if plot_raw_signal:
					raw_signal = regstim.get_interval_raw_signal()
					
					# check, how far the signal should be drawn
					t_max = min(regstim.get_interval_length(), post_stimulus_timeframe)
					last_sample = ceil(len(raw_signal) * (t_max / regstim.get_interval_length()))
					raw_signal = raw_signal[range(0, last_sample)]
					
					# check how much space we have for scaling the raw data
					if index > 0:
						timediff_prev = regstim.get_timepoint() - regular_stimuli[index - 1].get_timepoint()
					else:
						timediff_prev = 2.0
						
					if index < len(regular_stimuli) - 1:
						timediff_next = regular_stimuli[index + 1].get_timepoint() - regstim.get_timepoint()
					else:
						timediff_prev = 2.0
						
					# then, calculate the space we have for plotting the raw values
					space_margin = .45 * min(timediff_prev, timediff_next)
					
					# scale the signal accordingly
					signal_scaling_factor = space_margin / max_signal_value
					raw_signal = [signal_scaling_factor * val + regstim.get_timepoint() for val in raw_signal]
					
					# create a linspace to have an x-axis for the values
					signal_time = np.linspace(0, t_max, len(raw_signal))
					plt.plot(signal_time, raw_signal, "b-", linewidth = .5)
			
		# then, the actpots that presumably belong to this track
		for actpot in action_potentials:
			# get previous stimulus and its timestamp
			prev_stimulus = actpot.get_prev_reg_el_stimulus()
			prev_timept = prev_stimulus.get_timepoint()
			
			if prev_timept > time_start and prev_timept < time_stop:
				plt.scatter(x = actpot.get_dist_to_prev_reg_el_stimulus(), y = prev_stimulus.get_timepoint(), marker = "x", color = "r")
	
		plt.xlabel("Response Latency (s)")
		plt.ylabel("Time (s)")
		plt.gca().margins(x = 0.1)
	
		# invert the y-axis so that 0 is on top and the time increases downwards
		plt.gca().invert_yaxis()
		
		plt.show()
	
		self.fig = fig
	
	# TODO implement saving of the plot
	def save_to_file(self, filename):
		self.fig.savefig(fname = filename, dpi = 400)
		print("Figure saved.")
		
	'''