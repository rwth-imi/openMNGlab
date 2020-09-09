import tkinter as tk
import pygubu
import pandas as pd
from importers import SpikeImporter

## This class provides a GUI for importing spike files.
class SpikeImportGUI:

	## Path to the snooped/loaded file
	filepath = None

	## List of channels in the current file
	channels = []
	## Selected time channel
	time_channel = None
	## Selected signal channel
	signal_channel = None
	## A dictionary of selected stimuli channels. Use keys "regular_electrical", "force" and "extra_electrical"
	stimulus_channels = dict()
	## List of channels where AP wavemarks are stored
	ap_channels = []

	## The force threshold above which a force event is detected
	force_threshold = None
	## Max gap between two signal values for the AP wavemarks s.t. the values are still considered as belonging to a single AP
	max_ap_gap = None

	## Pygubu builder object
	builder = None
	
	## Tk toplevel widget
	main_window = None
	
	## Tk boolean value associated to the "load mech." checkbox
	load_mech = None
	## Tk boolean value associated to the "load extra electrical" checkbox
	load_ex_el = None
	
	## This function enables/disables the widget "obj" depending on the value of "enable". We use this to enable the boxes iff the corresponding checkbox is checked
	def enable_obj(obj, enable):
		if enable == True:
			obj['state'] = "normal"
		else:
			obj['state'] = "disabled"
			
	## Helper to enable or disable multiple objects at once
	def enable_objs(objs, enable):
		for obj in objs:
			SpikeImportGUI.enable_obj(obj, enable)

	## snoops a file and returns the names of the columns, i.e. the channel names
	# @param filepath Path to the CSV file
	def get_channel_names(filepath):
		# read the first csv line using pandas to get the column names
		file_head = pd.read_csv(filepath_or_buffer = filepath, nrows = 1, header = 0)
		channels = file_head.columns.values
		# for compatibility reasons, we need to replace the apostrophes by quotation marks
		channels = [channel.replace("'", "\"") for channel in channels]

		return channels
	
	## This method loads a spike file and saves the important info given through the GUI: \n
	# - it saves the time and signal channels \n
	# - it saves a dict of the chosen stimuli channel \n
	# - it saves a list of the AP channels
	def load_spikefile(self):	
		# get names of the chosen time and signal channels
		self.time_channel = self.builder.get_object('sel_time').get()
		self.signal_channel = self.builder.get_object('sel_signal').get()
		
		# get the names of the stimulus channels (if desired)
		self.stimulus_channels["regular_electrical"] = self.builder.get_object('sel_reg_el').get()
		
		if self.load_mech.get() == True:
			self.stimulus_channels["force"] = self.builder.get_object('sel_mech').get()
			
		if self.load_ex_el.get() == True:
			self.stimulus_channels["extra_electrical"] = self.builder.get_object('sel_ex_el').get()
			
		# get the AP channels
		lst_ap = self.builder.get_object('lst_ap')
		self.ap_channels = [self.channels[idx] for idx in lst_ap.curselection()]
		
		if (self.load_mech.get() == True):
			self.force_threshold = float(self.builder.get_object("txt_forcethresh").get())
		self.max_ap_gap = float(self.builder.get_object("txt_maxgap").get())
		
		self.main_window.destroy()
	
	## if a file is selected by the user, the UI will "snoop" the file s.t. it gets the channel names. These are then written into the comboboxes, which are enabled etc.
	def snoop_spikefile(self):
		self.filepath = self.builder.get_object("file_spike")['path']
		
		# get the channel names
		self.channels = SpikeImportGUI.get_channel_names(self.filepath)
		
		# activate all of the combo boxes
		comboboxes = ["sel_time", "sel_signal", "sel_reg_el"]
		for box in comboboxes:
			box_obj = self.builder.get_object(box)
			box_obj['state'] = "normal"
			box_obj['values'] = self.channels
			
		self.builder.get_object("sel_mech")['values'] = self.channels
		self.builder.get_object("sel_ex_el")['values'] = self.channels
			
		# initialize checkboxes
		chk_mech = self.builder.get_object('chk_mech')
		chk_mech['state'] = "normal"
		chk_mech['variable'] = self.load_mech
		chk_mech['command'] = lambda: SpikeImportGUI.enable_objs([self.builder.get_object('sel_mech'), self.builder.get_object('txt_forcethresh')], self.load_mech.get())
		
		chk_ex_el = self.builder.get_object('chk_ex_el')
		chk_ex_el['state'] = "normal"
		chk_ex_el['variable'] = self.load_ex_el
		chk_ex_el['command'] = lambda: SpikeImportGUI.enable_obj(self.builder.get_object('sel_ex_el'), self.load_ex_el.get())
		
		# initialize the AP channel list box
		lst_ap = self.builder.get_object('lst_ap')
		lst_ap['state'] = "normal"
		for ch in self.channels:
			lst_ap.insert(tk.END, ch)
			
		txt_maxgap = self.builder.get_object('txt_maxgap')
		txt_maxgap['state'] = "normal"
		txt_maxgap.insert(0, "0.005")
	
	## Construct the wrapper class for the GUI
	def __init__(self):
		self.builder = pygubu.Builder()
		self.builder.add_from_file('./gui/spike_import.ui')
		
		# get some important widgets from the form
		self.main_window = self.builder.get_object('toplevel_window')
		
		# register callbacks for the GUI buttons
		self.builder.get_object('btn_snoop')['command'] = self.snoop_spikefile
		self.builder.get_object('btn_loadfile')['command'] = self.load_spikefile
		
		# create varialbes for the checkbox values
		self.load_mech = tk.BooleanVar()
		self.load_ex_el = tk.BooleanVar()
		
		self.main_window.mainloop()
