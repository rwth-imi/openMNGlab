from recordings.mng_recording import MNGRecording
from importers.mng_importer import MNGImporter
from typing import List, Dict
import pandas as pd
import numpy as np

# import our own classes for the signal artifacts
from signal_artifacts import ActionPotential
from signal_artifacts import ElectricalStimulus
from signal_artifacts import MechanicalStimulus
from signal_artifacts import ElectricalExtraStimulus

## This class imports Spike2 experiments after they have been exported as CSV files
class SpikeImporter(MNGImporter):
	## The pandas dataframe as read from the CSV file
	df = None
	## Column name of the time column in the DF
	time_channel = None
	## Name of the signal column
	signal_channel = None
	
	## Constructs an importer object by reading the CSV and setting basic parameters for further processing
	# @param filepath Path to the csv file
	# @param time_channel Name of the time column
	# @param signal_channel Name of the signal column
	# @param sampling_rate Sampling rate of the MNG experiment
	# @param custom_delimiter Delimiter by which the columns in the CSV are separated
	# @param remove_apostrophes Removes the apostrophes which are somehow added by Spike2 but cause confusion in python
	def __init__(self, filepath, time_channel, signal_channel, sampling_rate = 20000, custom_delimiter = ",", remove_apostrophes = True):
		# set up pandas to expect NaN values in the data and load the file 
		self.df = pd.read_csv(filepath_or_buffer = filepath, delimiter = custom_delimiter, na_values = "NaN", na_filter = True)
		
		# remove the apostrophes from the column names
		if remove_apostrophes == True:
			self.df.columns = [column.replace("'", "") for column in self.df.columns]
			
		# write the channel names into our class variables
		self.time_channel = time_channel
		self.signal_channel = signal_channel
		self.sampling_rate = sampling_rate
			
	## TODO add comments for this method
	def create_recording(self, stimulus_channels: Dict[str, str], ap_channels: List[str], force_threshold = 0.5, max_ap_gap_time = 0.05) -> MNGRecording:

		# extract the regular electrical stimuli from the dataframe
		if "regular_electrical" in stimulus_channels:
			el_stimuli = self.get_electrical_stimuli(regular_stimulus_channel = stimulus_channels["regular_electrical"])
		else:
			# we need to set a default value here, in case that extra stimuli events are given but no regular stimulation channel was specified
			el_stimuli = []
			
		# same for the force stimuli
		if "force" in stimulus_channels:
			mech_stimuli = self.get_mechanical_stimuli(force_channel = stimulus_channels["force"], threshold = force_threshold, max_gap_time = 0.005)
		else:
			mech_stimuli = None
			
		# and the extra electical ones
		if "extra_electrical" in stimulus_channels:
			ex_el_stimuli = self.get_extra_stimuli(extra_stimulus_channel = stimulus_channels["extra_electrical"], regular_el_stimuli = el_stimuli)
		else:
			ex_el_stimuli = None
			
		# then, get all the action potentials and the raw signal
		actpots = self.get_action_potentials(max_gap_time = max_ap_gap_time, ap_marker_channels = ap_channels)
		raw_signal = self.get_raw_signal_split_by_stimuli(el_stimuli = el_stimuli, verbose = False)
		
		# finally, some attributes about the recording itself
		t_start, t_end = self.get_time_range()
		sampling_rate = self.sampling_rate
		
		# create and return an MNG Recording object
		return MNGRecording(raw_signal = raw_signal, el_stimuli = el_stimuli, actpots = actpots, t_start = t_start, t_end = t_end, \
			sampling_rate = sampling_rate, mech_stimuli = mech_stimuli, extra_el_stimuli = ex_el_stimuli)

	## Get the minimum and maximum timestamps from this recording
	def get_time_range(self):
		return min(self.df[:][self.time_channel].values), max(self.df[:][self.time_channel].values)
			
	## Get the whole pandas dataframe for the recording
	def get_raw_dataframe(self):
		return self.df
			
	## Get only the raw signal from the recording
	def get_raw_signal(self) -> List[float]:
		return self.df[:][self.signal_channel].values
		
	## Get the raw signal, chopped by the regular stimuli.
	# It is preferable to provide a time range, else this will take forever...
	# @param el_stimuli List of electrical stimuli in the recording
	# @param start_time Minimum timestamp of the intervals
	# @param stop_time Maximum timestamp for the intervals
	def get_raw_signal_split_by_stimuli(self, el_stimuli, verbose = False, start_time = 0, stop_time = float("infinity")) -> List[List[float]]:
		raw_signal = self.df[:][self.signal_channel]
		raw_intervals = []
	
		try:
			# cut out an interval for each of the stimuli
			stimulus_iter = iter(el_stimuli)
			stimulus = next(stimulus_iter)
			
			# find the first interval that lies within the desired range
			while stimulus.timepoint < start_time:
				stimulus = next(stimulus_iter)
				
			if verbose == True:
				print("Starting at " + str(stimulus.timepoint) + "s")
			
			while True:				
				# get the next stimulus to search for the end
				next_stimulus = next(stimulus_iter)
								
				# retrieve this interval from the dataframe
				raw_interval = self.df.iloc[range(stimulus.df_index, next_stimulus.df_index)][self.signal_channel].values
				stimulus.interval_raw_signal = raw_interval
				stimulus.interval_length = next_stimulus.timepoint - stimulus.timepoint
				raw_intervals.append(raw_interval)
				
				if verbose == True:
					print("Cropped interval from " + str(stimulus.timepoint()) + "s to " + str(next_stimulus.timepoint()) + "s")
				
				# this second stimulus is also the beginning of the next interval
				stimulus = next_stimulus
				
				# STOP if we exceeded the desired time range
				if next_stimulus.timepoint > stop_time:
					break
			
		# this exception will be thrown if we reached the last stimulus
		except StopIteration:
			index_stop = len(self.df.index)
			
			# retrieve this interval from the dataframe
			raw_interval = self.df.iloc[range(stimulus.df_index, index_stop)][self.signal_channel].values
			stimulus.raw_signal = raw_interval
			raw_intervals.append(raw_interval)
			
		print("Done with cropping the intervals")
			
		return raw_intervals
			
	## Gets a list of action potentials provided in the selected marker channels.
	# The function looks at the channels and selects sections from the dataframe where the entries in the channels are not NaN.
	# @param ap_marker_channels List of channels where wavemarks of APs are contained
	# @param max_gap_time If the gap between two consecutive not-NaN values in a channel is larger than this time, they are considered as two separate APs
	# @param el_stimuli List of electrical stimuli
	def get_action_potentials(self, ap_marker_channels, max_gap_time = 0.005, verbose = False) -> List[ActionPotential]:
		# catch some possible errors errors
		# TODO: make sure that these errors cannot even occur
		if not ap_marker_channels:
			print("Getting APs from the signal itself is not yet supported.")
			return None		
			
		# get the APs from all marker channels
		actpots = []
		for channel_index, ap_marker_channel in enumerate(ap_marker_channels):	
			# get the rows from the AP where Spike registered some AP matching our template
			actpots_df = self.__get_rows_where_not_nan(ap_marker_channel)
			
			# then, create a list of the APs in this channel
			
			index = 0
			while index < len(actpots_df.index) - 1:
				# assume that the first index is always the onset of an AP
				onset = index
				
				len_df = len(actpots_df.index)
				# increase the DF(!) index as long as the time distance to the next row is small enough
				while (abs(actpots_df.iloc[index + 1][self.time_channel] - actpots_df.iloc[index][self.time_channel]) < max_gap_time):
					index = index + 1
					# break out of the loop if we reached the end
					if (index == len_df - 1):
						break
					
				# then, this is the last index
				offset = index
					
				# create AP object from the shortened dataframe
				# range does not include the last position, therefore + 1 !
				# also, pass the electrical stimuli so that the class can get the closest one
				# print(str(onset) + " to " + str(offset))
				ap = ActionPotential.from_dataframe(input_df = actpots_df.iloc[range(onset, offset + 1)], channel_index = channel_index, verbose = verbose)
				actpots.append(ap)
				
				# "jump" to the next AP
				index = index + 1
				
			print("Finished processing AP channel " + str(channel_index + 1) + " out of " + str(len(ap_marker_channels)))
	
		print("List of APs created.")
		return actpots
		
	## Get a list of the extra (interposed) stimuli.
	# Two electrical stimuli are put into a single instance of the "extra stimulus" object if their distance is less than max_gap_time.
	# From the thus created train of stimuli, we can then extract stuff such as number of stimuli, frequency and distance to next regular stimulus.
	# @param extra_stimulus_channel The channel in which the extra stimuli are listed
	# @param regular_el_stimuli List of the regular electrical stimuli
	# @param max_gap_time The max. gap between two consecutive stimuli so that they are considered as belonging to the same event
	def get_extra_stimuli(self, extra_stimulus_channel, regular_el_stimuli, max_gap_time = 1.0, verbose = False) -> List[ElectricalExtraStimulus]:
		# get rows where stimulus channel is one (where stimulus fired)
		ex_stimuli_df = self.__get_rows_where_equals_one(extra_stimulus_channel)
		len_df = len(ex_stimuli_df.index)
	
		# go over the dataframe to identify "stimulus trains"
		el_ex_stimuli = []
		index = 0
		while index < len_df - 1:
			# start with an empty list
			stimuli_train = []
			# but immediately add the first stimulus
			stimuli_train.append(ElectricalStimulus.from_dataframe(input_data = ex_stimuli_df.iloc[index], df_index = index, verbose = verbose))
			
			# increase the DF(!) index as long as the time distance to the next row is small enough
			while (abs(ex_stimuli_df.iloc[index + 1][self.time_channel] - ex_stimuli_df.iloc[index][self.time_channel]) < max_gap_time):
				# the distance is small enough, so jump to next row and add the stimulus to the current train
				index = index + 1
				stimuli_train.append(ElectricalStimulus.from_dataframe(input_data = ex_stimuli_df.iloc[index], df_index = index, verbose = verbose))
				
				# break out of the loop if we reached the end
				if (index == len_df - 1):
					break
				
			# create the object for the electrical extra stimulus
			# that is created from the list of the stimulus train
			# and requires the list of regular frequent stimuli
			# to calucate the distances
			el_ex_stimulus = ElectricalExtraStimulus(extra_el_stimuli = stimuli_train, regular_stimuli = regular_el_stimuli, verbose = verbose)
			el_ex_stimuli.append(el_ex_stimulus)
			
			# "jump" to the next train of stimuli
			index = index + 1
				
		print("List of extra eletrical stimuli created.")
		return el_ex_stimuli
		
	## Get a list of the regular electrical stimuli in the recording
	# @param regular_stimulus_channel Channel name for the regular stimuli
	def get_electrical_stimuli(self, regular_stimulus_channel, verbose = False) -> List[ElectricalStimulus]:
		# get rows where stimulus channel is one (where stimulus fired)
		stimuli_df = self.__get_rows_where_equals_one(regular_stimulus_channel)
		
		# put all the stimuli into a list object
		el_stimuli = []
		for index, row in stimuli_df.iterrows():
			es = ElectricalStimulus.from_dataframe(input_data = row, df_index = index, verbose = verbose)
			el_stimuli.append(es)
		
		print("List of eletrical stimuli created.")
		return el_stimuli
		
	## Get a list of mechanical stimulation events
	# @param force_channel Column name of the channel with force information
	# @param threshold Threshold above which a force is considered a mechanical stimulus
	# @param max_gap_time Max time for which the force value can drop below the threshold without creating two separate force stimuli
	def get_mechanical_stimuli(self, force_channel, threshold, max_gap_time, verbose = False) -> List[MechanicalStimulus]:
		# get rows where force channel exceeds threshold
		force_df = self.__get_rows_where_exceeds_threshold(channel_name = force_channel, threshold = threshold)
		
		# then, create a list of the APs in this channel
		mech_stimuli = []
		index = 0
		while index < len(force_df.index) - 1:
			# assume that the first index is always the onset of an AP
			onset = index
			
			len_df = len(force_df.index)
			# increase the DF(!) index as long as the time distance to the next row is small enough
			while (abs(force_df.iloc[index + 1][self.time_channel] - force_df.iloc[index][self.time_channel]) < max_gap_time):
				index = index + 1
				# break out of the loop if we reached the end
				if (index == len_df - 1):
					break
				
			# then, this is the last index
			offset = index
				
			# create MS object from the shortened dataframe
			# range does not include the last position, therefore + 1 !
			# also, pass the electrical stimuli so that the class can get the closest one
			# print(str(onset) + " to " + str(offset))
			ms = MechanicalStimulus.from_dataframe(input_df = force_df.iloc[range(onset, offset + 1)], verbose = verbose)
			mech_stimuli.append(ms)
			
			# "jump" to the next AP
			index = index + 1
	
		print("List of mechanical stimuli created.")
		return mech_stimuli
		
		print(force_df)
		
		return
		
	## Helper to get rows from DF where a certain column equals one
	def __get_rows_where_equals_one(self, channel_name):
		return self.df[self.df[channel_name] == 1]
		
	## Helper to get rows from DF where a certain column is unequal to NaN
	def __get_rows_where_not_nan(self, channel_name):
		return self.df[~np.isnan(self.df[channel_name])]
		
	## Helper to get rows from DF where a column exceeds a threshold
	def __get_rows_where_exceeds_threshold(self, channel_name, threshold):
		return self.df[self.df[channel_name] > threshold]