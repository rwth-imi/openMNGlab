import pandas as pd
import numpy as np

class SpikeImporter:
	# the dataframe that we work with
	df = None
	
	# constructor loads a spike file from the given file path
	def __init__(self, filepath, custom_delimiter = ",", remove_apostrophes = True):
		# set up pandas to expect NaN values in the data and load the file 
		self.df = pd.read_csv(filepath_or_buffer = filepath, delimiter = custom_delimiter, na_values = "NaN", na_filter = True)
		
		# remove the apostrophes from the column names
		if remove_apostrophes == True:
			self.df.columns = [column.replace("'", "") for column in self.df.columns]
			
	def getRawDataframe(self):
		return self.df
			
	# return the action potentials from one channel
	def getActionPotentials(self, channel_name):
		return self.getRowsWhereNotNaN(channel_name)
		
	# helper function to return rows that are unequal NaN
	def getRowsWhereNotNaN(self, channel_name):
		return self.df[~np.isnan(self.df[channel_name])]
		
	# return the electrical pulses from the digmark channel
	def getElectricalStimuli(self, channel_name):
		return self.getRowsWhereEqualsOne(channel_name)
		
	# helper function that return rows where channel is one
	def getRowsWhereEqualsOne(self, channel_name):
		return self.df[self.df["32 DigMark"] == 1]