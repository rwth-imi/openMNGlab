# openMNGlab

!IMPORTANT UPDATE 21.04.2022!
We are currently working on the new version of the software, with substantial restructuring of the code. If you are interested in analysing your microneurography data, please contact Ekaterina Kutafina (ekutafina * at * ukaachen.de) for the details.



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

## Test data

For testing the jupyter notebooks, we provide some test data that can be found [here](https://gin.g-node.org/ekaterina_kutafina/openMNGlab_DataTest). Right now there is test data for Spike2. The Dapsys test data will be following.

## Citation

If you want to cite this framework, use the following citation from this [paper](https://pubmed.ncbi.nlm.nih.gov/34545832/): 
Schlebusch F, Kehrein F, Röhrig R, Namer B, Kutafina E. openMNGlab: Data Analysis Framework for Microneurography - A Technical Report. Stud Health Technol Inform. 2021 Sep 21;283:165-171. doi: 10.3233/SHTI210556. PMID: 34545832.
