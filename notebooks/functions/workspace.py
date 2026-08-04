from pathlib import Path

class Workspace:
    def __init__(self, workspace_path: Path|str):
        self.path = Path(workspace_path) if isinstance(workspace_path, str) else workspace_path
        if not self.path.exists():
            raise FileNotFoundError(f"Workspace path {self.path} does not exist.")                
        self.name = self.path.name
        self.results_path = self.path / "results"
        self.summaries_path = self.path / "summaries" / self.name
        self.metadata_path = self.path / "metadata"
        self.master_csv_path = self.metadata_path / f"{self.name}.csv"