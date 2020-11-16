from typing import List, Iterable
import os, csv
from pathlib import Path
from tqdm import tqdm
import numpy as np
import pandas as pd
import re

## A single action potential (AP) in a recording.
# \author Fabian Schlebusch, fabian.schlebusch@rwth-aachen.de
class ActionPotential:
	## The onset of this AP (in seconds).
	onset = None
	## The offset of this AP (in seconds).
	offset = None
	
	## The raw signal values that have been extracted from the recording.
	raw_signal = None
	
	## A dictionary(!!!) where the features as imputed by the feature extraction can be saved.
	# usage: e.g., my_ap.features["latency"] = calculate_latency(...)
	features = None
	
	## Some algorithms use this variable to store the "imputed" fibre index.
	# e.g., fibre_tracking.dbscan_clustering.DBSCANClustering writes its prediction into this variable.
	# In the future, this variable will probably be kicked out in favour of a C-fibre object that bundles information in a more "real-life entity".
	implied_fibre_index = None
	
	## The index of the spike channel from which this action potential was extracted.
	# See importers.spike_importer.SpikeImporter for further info.
	channel_index = None
	
	## The last stimulus of each kind (i.e., regular electrical, mechanical, ...) is tracked in this dictionary.
	# We agreed on some nomenclature to store these stimuli in the dict without causing too many conflicts: \n
	# "regular": the previous regular electrical stimulus \n
	# "mechanical": the previous mechanical stimulus \n
	# "extra_electrical": the previous electrical extra stimulus
	prev_stimuli = None
	
	## If a stimulus event triggers an AP, keep a reference from the AP to the stimulus event.
	# e.g., force events may be causing multiple APs, then keep a reference from the AP to the event which caused it.
	triggered_by = None
	
	## This is the max. time for which we assume that there is a causal link between a stimulus and a triggered AP.
	# some algorithms use this constant to make a link between the two objects.
	CAUSAL_DIST = 0.010
	
	## Constructs an AP object
	# @param onset Onset of the AP (s)
	# @param offset Offset of the AP (s)
	# @param raw_signal The raw values from the MNG recording for this particular AP
	# @param verbose Check True if the AP class should print some info about itself upon creation.
	def __init__(self, onset, offset, raw_signal, verbose = False):
		# set some fundamental attributes of the AP
		self.onset = onset
		self.offset = offset
		self.raw_signal = raw_signal
		self.features = dict()
		self.prev_stimuli = dict()
	
		if verbose == True:
			self.print_info()

	## Construct an AP class from a pandas dataframe which contains only the rows for this AP
	# @param input_df The pandas dataframe object
	# @param time_column Name of the column which contains the time stamps
	# @param signal_column Name of the column which contains the signal values
	# @param channel_index Index of the channel from which the AP was extracted
	# @return AP object created from the dataframe
	def from_dataframe(input_df, time_column = "Time", signal_column = "1 Signal", channel_index = 0, verbose = False):
		# get on- and offset (in seconds) for this AP
		onset = input_df.iloc[0][time_column]
		offset = input_df.iloc[-1][time_column]
		
		ap = ActionPotential(onset = onset, offset = offset, raw_signal = input_df[signal_column].values, verbose = verbose)
		
		# set the channel index, e.g. for different marker shapes in a scatter plot
		ap.channel_index = channel_index

		return ap
				
	## Prints info about this action potential, e.g., for debugging purposes
	def print_info(self):
		print("Found action potential with:")
		print("onset = " + str(self.onset) + "s offset = " + str(self.offset) + "s")
		
	## Method for saving a list of APs to a CSV file
	# @param actpots List of action potentials
	# @param fpath File path where the APs should be written to
	@staticmethod
	def save_aps_to_csv(actpots: List, fpath):
		# create the directory (if it does not already exist)
		Path(os.path.basename(fpath)).mkdir(parents = True, exist_ok = True)

		# get a list of all features in this list of actpots
		features = []
		# iterate over all keys for all action potentials to get an overview over the features
		for ap in actpots:
			for key in ap.features.keys():
				# construct the feature name as we want it in the dict
				feature_key = "feature_" + key
				if not feature_key in features:
					# add the prefix "feature_" s.t. we know what are features upon loading the file later
					features.append(feature_key)

		with open(fpath, 'w', newline = '\n') as file:
			# create writer and write the file header
			csv_writer = csv.writer(file, delimiter = ";", quotechar = "\"")
			header_fields = ["onset", "offset", "channel_idx"] + features
			csv_writer.writerow(header_fields)

			# now, write each of the APs into the csv file
			for ap in tqdm(actpots):
				# allocate a list where we can put the AP's stuff
				ap_row = [str(ap.onset), str(ap.offset), str(ap.channel_index)]
				ap_row.extend([""] * (len(header_fields) - 3))

				# now, write the features
				for key, value in ap.features.items():
					# construct the key of this feature in the csv and find the index
					feature_key = "feature_" + key
					feature_idx = header_fields.index(feature_key)
					# then, write the feature value at the index position
					# makeing sure that iterables are separated by commata!
					if isinstance(value, Iterable) and not isinstance(value, str):
						ap_row[feature_idx] = "[" + ",".join([str(v) for v in value]) + "]"
					else:
						ap_row[feature_idx] = str(value)

				# finally, write this row to the disk
				csv_writer.writerow(ap_row)

	## Load the list of APs from the given csv file
	# @param fpath Path to the csv file from which the APs should be loaded
	@staticmethod
	def load_aps_from_csv(fpath):
		# read the given file into a dataframe object
		ap_df = pd.read_csv(filepath_or_buffer = fpath, sep = ";")	

		# we define a regular expression for string representations of lists
		list_regex = re.compile("(\s)*\[.*\](\s)*")

		# allocate the list of APs
		aps = []

		# iterate over all the rows
		for ap_idx, ap_row in tqdm(ap_df.iterrows(), total = len(ap_df.index)):
			# get the basic information about the AP
			onset = ap_row["onset"]
			offset = ap_row["offset"]
			channel_idx = ap_row["channel_idx"]
			# TODO get the raw signal
			raw_signal = None
			
			# now, we create the AP object s.t. we can write the features into its feature dict
			ap = ActionPotential(onset = onset, offset = offset, raw_signal = raw_signal)
			# also, set the channel index
			ap.channel_index = channel_idx
			
			# iterate over the remaining series items to get the features
			for key, value in ap_row[3 : ].iteritems():
				# check if the order of the entries is valid
				if not key.startswith("feature_"):
					raise ValueError("The AP file has an invalid format as there are non-feature keys following the basic info.")
				# if it is indeed valid, we can get the name of the feature
				feature_name = key[len("feature_") :]
				# now, we either have a List or some simple value
				if isinstance(value, str) and list_regex.match(value):
					# get indices of the start and stop indices of the list
					start_idx, stop_idx = value.index("["), value.index("]")
					# now, retrieve the values
					lst_values = value[start_idx + 1 : stop_idx].split(",")
					ap.features[feature_name] = lst_values
				else:
					ap.features[feature_name] = value
					
			# now, append the ap to the list of aps
			aps.append(ap)

		return aps

	## The implied duration of this AP.
	@property
	def duration(self):
		return self.offset - self.onset