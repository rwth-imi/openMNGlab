import pandas as pd
import numpy as np

import signal_artifacts
# reload the signal_artifacts classes
# hacky workaround atm
import importlib
importlib.reload(signal_artifacts)

# import our own classes for the signal artifacts
from signal_artifacts import ActionPotential
from signal_artifacts import ElectricalStimulus
from signal_artifacts import MechanicalStimulus

class SpikeImporter:
	# the dataframe that we work with
	df = None
	# save the channel names here to ease usage of this class from the outside
	time_channel = None
	signal_channel = None
	stimulus_channel = None
	ap_marker_channels = None
	force_channel = None
	
	# constructor loads a spike file from the given file path
	def __init__(self, filepath, time_channel, signal_channel, stimulus_channel, ap_marker_channels = [], force_channel = None, custom_delimiter = ",", remove_apostrophes = True):
		# set up pandas to expect NaN values in the data and load the file 
		self.df = pd.read_csv(filepath_or_buffer = filepath, delimiter = custom_delimiter, na_values = "NaN", na_filter = True)
		
		# remove the apostrophes from the column names
		if remove_apostrophes == True:
			self.df.columns = [column.replace("'", "") for column in self.df.columns]
			
		# write the channel names into our class variables
		self.time_channel = time_channel
		self.signal_channel = signal_channel
		self.stimulus_channel = stimulus_channel
		self.ap_marker_channels = ap_marker_channels
		if not ap_marker_channels:
			print("No AP marker channel was given. But AP detection from signal is not yet implemented!")
		self.force_channel = force_channel
			
	def getRawDataframe(self):
		return self.df
			
	# return a list of action potentials for the gap times
	# also, calculate the distance to the electrical stimuli
	def getActionPotentials(self, max_gap_time, el_stimuli):
		# catch some possible errors errors
		# TODO: make sure that these errors cannot even occur
		if not self.ap_marker_channels:
			print("Getting APs from the signal itself is not yet supported.")
			return None
		if el_stimuli == None:
			print("Please give a list of the electrical stimuli in this measurement")
			return None
			
		# get the APs from all marker channels
		actpots = []
		for ap_marker_channel in self.ap_marker_channels:	
			# get the rows from the AP where Spike registered some AP matching our template
			actpots_df = self.getRowsWhereNotNaN(ap_marker_channel)
			
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
				ap = ActionPotential(input_df = actpots_df.iloc[range(onset, offset + 1)], el_stimuli = el_stimuli)
				actpots.append(ap)
				
				# "jump" to the next AP
				index = index + 1
	
		print("List of APs created.")
		return actpots
				
	# return the electrical pulses from the digmark channel
	def getElectricalStimuli(self):
		# get rows where stimulus channel is one (where stimulus fired)
		stimuli_df = self.getRowsWhereEqualsOne(self.stimulus_channel)
		
		# put all the stimuli into a list object
		el_stimuli = []
		for index, row in stimuli_df.iterrows():
			es = ElectricalStimulus(input_data = row)
			el_stimuli.append(es)
		
		print("List of eletrical stimuli created.")
		return el_stimuli
		
	# return list of mechanical stimlui from the force channel
	def getMechanicalStimuli(self, threshold, max_gap_time):
		# get rows where force channel exceeds threshold
		force_df = self.getRowsWhereExceedsThreshold(channel_name = self.force_channel, threshold = threshold)
		
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
			ms = MechanicalStimulus(input_df = force_df.iloc[range(onset, offset + 1)])
			mech_stimuli.append(ms)
			
			# "jump" to the next AP
			index = index + 1
	
		print("List of mechanical stimuli created.")
		return mech_stimuli
		
		print(force_df)
		
		return
		
	# helper function that return rows where channel is one
	def getRowsWhereEqualsOne(self, channel_name):
		return self.df[self.df[channel_name] == 1]
		
	# helper function to return rows that are unequal NaN
	def getRowsWhereNotNaN(self, channel_name):
		return self.df[~np.isnan(self.df[channel_name])]
		
	# helper function to get rows that exceed a certain threshold
	def getRowsWhereExceedsThreshold(self, channel_name, threshold):
		return self.df[self.df[channel_name] > threshold]