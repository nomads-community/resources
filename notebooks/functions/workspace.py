from pathlib import Path

import yaml

def extract_config_values(config_file: Path = "../config.yaml") -> dict:
    """
    Extracts configuration values from the specified yaml file and returns them as a dictionary.
    """
    config_file = Path(config_file).expanduser().resolve()
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file {config_file.name} does not exist in {config_file.parent}.\n"
                                "Create it by copying the `example_config.yml` file in the notebooks folder, and save it as `config.yml` in the same folder, then edit its contents as appropriate.\n")
    
    with config_file.open("r") as f:
        config = yaml.safe_load(f) or {}

    if not isinstance(config, dict):
        raise ValueError(f"Expected a mapping at the top level of {config_file}, got {type(config).__name__}.")
    return config   

class Workspace:   
    def __init__(self, config_file: str = "../config.yaml"):
        self.config_path = Path(config_file).expanduser().resolve()
        self.config_dict = extract_config_values(self.config_path)
        self.categories = self.config_dict.get("categories", [])
        self.path = self.resolve_workspace_dir()
        self.name = self.path.name
        self.results_path = self.path / "results"
        self.summaries_path = self.path / "summaries" / self.name
        self.metadata_path = self.path / "metadata"
        self.master_csv_path = self.metadata_path / f"{self.name}.csv"
        print(f"Workspace loaded: {self.name} from {self.path}")

    def resolve_workspace_dir(self) -> Path:
        """
        Pull and check workspace is valid from config dict
        """
        ws_dir = self.config_dict.get("workspace_dir", None)
        if not ws_dir:
            raise ValueError(f"No workspace_dir=\"path_to_workspace\" found. Please add to the config file")

        ws_path = Path(ws_dir).expanduser().resolve()
        if not ws_path.exists():
            raise FileNotFoundError(f"Workspace path {ws_path} does not exist")
        return ws_path
