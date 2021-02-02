from typing import Union, Dict, List, Any, Type, Iterable, Tuple, Type, Set
from features.feature import Feature
from features.extraction.feature_extractor import FeatureExtractor
from neo_importers.neo_wrapper import MNGRecording
from pathlib import Path
from copy import deepcopy
import yaml

class FeatureDatabase:
    def __init__(self, data_directory: Path, recording: MNGRecording, feature_classes: Set[Type[Feature]] = {Feature}):
        assert not data_directory.is_file()
        data_directory.mkdir(parents=True, exist_ok=True)
        self.recording: MNGRecording = recording
        self.data_directory: Path = data_directory
        self.class_types = {class_type.__name__: class_type for class_type in feature_classes}
        
        self.channel_features: Dict[str, Dict[str, Feature]] = {}
    
    def __getitem__(self, key: Union[str, Tuple[str, str]]) -> Union[Dict[str, Feature], Feature]:
        if isinstance(key, str):
            return self.channel_features[key]
        assert isinstance(key, tuple)
        assert len(key) == 2
        return self.channel_features[key[0]][key[1]]
    
    def __setitem__(self, key: Union[str, Tuple[str, str]], value: Union[Dict[str, Feature], Feature]) -> None:
        if isinstance(key, str):
            assert isinstance(value, dict)
            self.channel_features[key] = value
        assert isinstance(key, tuple)
        assert len(key) == 2
        assert isinstance(value, Feature)
        sub_dict = self.channel_features.get(key[0], {})
        sub_dict[key[1]] = value
        self.channel_features[key[0]] = sub_dict
    
    def _store_features(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        result = {}
        for ch_name, features in self.channel_features.items():
            ch_features: Dict[str, Dict[str, Any]] = {}
            for feature_name, feature in features.items():
                feature_data = feature.store(self.data_directory)
                feature_data["class_type"] = feature.__class__.__name__
                ch_features[feature_name] = feature_data
            result[ch_name] = ch_features
        return result

    def store(self) -> None:
        database_data = {
            "recording": {
                "name": self.recording.name
            },
            "features": self._store_features()
        }
        if self.recording.file_name is not None:
            database_data["recording"]["file_name"] = self.recording.file_name
        with open(self.data_directory/"db.yml", "w") as fl:
            yaml.dump(database_data, fl)

    def load(self) -> None:
        with open(self.data_directory/"db.yml", "r") as fl:
            database_data = yaml.load(fl, Loader=yaml.FullLoader)
        assert self.recording.name == database_data["recording"]["name"]
        assert (self.recording.file_name is None and database_data["recording"].get("file_name") is None) \
            or (self.recording.file_name == database_data["recording"].get("file_name"))
        self.channel_features = {}
        for ch_name, features in database_data["features"].items():
            ch_features = {}
            for feature_name, feature_data in features.items():
                feature_class_name = feature_data["class_type"]
                feature_class_type = self.class_types[feature_class_name]
                feature = feature_class_type(feature_name, self.recording, ch_name)
                feature.load(feature_data, self.data_directory)
                ch_features[feature_name] = feature
            self.channel_features[ch_name] = ch_features
    
    def extract_features(self, channels: Union[str, Iterable[str]], extractor_class: Type[FeatureExtractor], **extractor_args) -> None:
        if isinstance(channels, str):
            channels = [channels]
        for channel in channels:
            extractor = extractor_class(recording=self.recording, **extractor_args)
            feature = extractor.create_feature(channel)
            self.add_feature(feature)
    
    def get_feature(self, channel_id: str, feature_name: str) -> Feature:
        return self.channel_features.get(channel_id, {}).get(feature_name)
    
    def add_feature(self, feature: Feature) -> None:
        channel_id = feature.channel.id
        self[channel_id, feature.name] = feature