from tests.helpers import download_files
import unittest
import os
from pathlib import Path

import neo

import neo_importers.neo_spike_importer as spike_importer
from neo_importers.neo_wrapper import MNGRecording

# PARAMETERS FOR THIS TEST
TEST_DIR_NAME = Path("..")/"resources"/"test"/"spike2"
FILENAMES = ["20_05_13_U1a_pulse_Latenz.smr"]
FILE_URLS = ["https://gin.g-node.org/fschlebusch/openMNGlab-testdata/raw/383db037d8e21ee9b3bdb1ebb8048f1f035eaa75/spike2/20_05_13_U1a_pulse_Latenz.smr"]

class Spike2ImporterTest(unittest.TestCase):

    def setUp(self) -> None:
        
        download_files(FILE_URLS, FILENAMES, TEST_DIR_NAME)

        return super().setUp()

    def test_spike2_import(self):
        fname = Path(os.path.join(TEST_DIR_NAME, FILENAMES[0]))

        self.assertTrue(os.path.exists(fname))
        bl, id_map = spike_importer.import_spike_file(fname, 
                                              stimuli_event_channels={"DigMark"},
                                              action_potential_channels={"nw-1#2"}
                                             )
        seg: neo.core.Segment = bl.segments[0]
        self.assertGreater(len(seg.spiketrains), 0)
        self.assertGreater(len(seg.events), 0)
        self.assertGreater(len(seg.analogsignals), 0)

        recording: MNGRecording = MNGRecording(bl.segments[0])

        self.assertGreater(len(recording.action_potential_channels), 0)
        self.assertGreater(len(recording.electrical_stimulus_channels), 0)
        self.assertGreater(len(recording.raw_data_channels), 0)