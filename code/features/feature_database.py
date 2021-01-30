from typing import Union, Dict, List, Any, Type, Iterable, Tuple
from features.feature import Feature, deserialize_units, serialize_units
from features.extraction.feature_extractor import FeatureExtractor
from neo_importers.neo_wrapper import MNGRecording
from pathlib import Path
from copy import deepcopy
import yaml

class FeatureDatabase:
    def __init__(self, data_directory: Path, recording: MNGRecording):
        assert not data_directory.is_file()
        data_directory.mkdir(parents=True, exist_ok=True)
        self.recording: MNGRecording = recording
        self.data_directory: Path = data_directory
        
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
    
    @staticmethod
    def _get_feature_file_name(ch_name: str, feature_name: str) -> str:
        return f"{ch_name}.{feature_name}.npy"

    def __get_database_data(self) -> Dict[str, Any]:
        result = {
            "recording": {
                "name": self.recording.name
            },
            "features": {
                ch_name: [
                    {
                        "name": f_name,
                        "data_file": self._get_feature_file_name(ch_name, f_name),
                        "units": serialize_units(feature.units),
                        "annotations": deepcopy(feature.annotations)
                    } for f_name, feature in features.items()
                ] for ch_name, features in self.channel_features.items()
            }
        }
        if self.recording.file_name is not None:
            result["recording"]["file_name"] = self.recording.file_name
        return result
    
    def store(self) -> None:
        database_data = self.__get_database_data()
        with open(self.data_directory/"db.yml", "w") as fl:
            yaml.dump(database_data, fl)
        for channel, features in self.channel_features.items():
            for feature_name, feature in features.items():
                file_name = self._get_feature_file_name(channel, feature_name)
                with open(self.data_directory/file_name, "wb") as fl:
                    feature.store_data(fl)

    def load(self) -> None:
        with open(self.data_directory/"db.yml", "r") as fl:
            database_data = yaml.load(fl, Loader=yaml.FullLoader)
        assert self.recording.name == database_data["recording"]["name"]
        assert (self.recording.file_name is None and database_data["recording"].get("file_name") is None) \
            or (self.recording.file_name == database_data["recording"].get("file_name"))
        self.channel_features = {}
        for ch_name, features in database_data["features"].items():
            ch_features = {}
            for feature_data in features:
                feature_name = feature_data["name"]
                feature_file = self.data_directory/feature_data["data_file"]
                feature_units = deserialize_units(feature_data["units"])
                feature = Feature(self.recording, ch_name, annotations=feature_data["annotations"])
                with open(feature_file, "rb") as fl:
                    feature.load_data(fl, feature_units)
                ch_features[feature_name] = feature
            self.channel_features[ch_name] = ch_features
    
    def extract_features(self, channels: Union[str, Iterable[str]], extractor_class: Type[FeatureExtractor], **extractor_args) -> None:
        if isinstance(channels, str):
            channels = [channels]
        for channel in channels:
            extractor = extractor_class(recording=self.recording, **extractor_args)
            name, feature = extractor.create_feature(channel)
            self.add_feature(name, feature)
    
    def get_feature(self, channel_id: str, feature_name: str) -> Feature:
        return self.channel_features.get(channel_id, {}).get(feature_name)
    
    def add_feature(self, feature_name: str, feature: Feature) -> None:
        channel_id = feature.channel.id
        self[channel_id, feature_name] = feature