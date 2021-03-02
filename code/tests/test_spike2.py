import unittest
import os
from pathlib import Path

import neo

import neo_importers.neo_spike_importer as spike_importer
from neo_importers.neo_wrapper import MNGRecording

# PARAMETERS FOR THIS TEST
SPIKE2_FILE_NAME = Path(".")/"tests"/"resources"/"spike2"/"20_05_13_U1a_pulse_Latenz.smr"

class Spike2ImporterTest(unittest.TestCase):

    def test_spike2_import(self):
        self.assertTrue(os.path.exists(SPIKE2_FILE_NAME))

        bl, id_map = spike_importer.import_spike_file(SPIKE2_FILE_NAME, 
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