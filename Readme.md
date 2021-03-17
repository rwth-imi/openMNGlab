# openMNGlab

This project aims at providing a software framework for data analysis on microneurography (MNG) recordings.
It currently supports import of data from the Spike2 and Dapsys data acquisition softwares.
However, due to its modular structure, new methods for data import can be added at any time.
Furthermore, it is possible to import arbitrary neo-objects through the HDF5 format.

## Installation

1. Clone this repository 
2. We recommend you to set up a virtual environment
3. Install the requirements from the requirements.txt
4. Optional: run the test classes to confirm that the installation works correctly
5. Optional: generate doxygen comments from the provided doxyfile

## Usage

We provide jupyter notebooks which show how Spike2 and Dapsys files can be imported.
Data is internally stored using the neo electrophysiology format.
However, there are wrappers like the ```MNGRecording``` which provide convenient access to the most important entities for MNG data analysis, including electrical stimulation events and action potentials.
For machine learning and regression analysis, we provide the ```FeatureDatabase``` where features can be registered.
Their expressions can be persistently stored as yaml and numpy files.
If you want to implement new features, you must implement the ```FeatureExtractor``` interface and register your feature with the ```FeatureDatabase```.