from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from pathlib import Path

import pandas as pd
from dates import extract_date


def check_if_group_root(path: Path) -> bool:
    """
    Check if the given path is a valid group folder.
    A valid group folder name ends with NOMADS_Share and has the form
    COUNTRY-GROUP-NOMADS_Share.
    """
    return path.name.endswith("NOMADS_Share") and len(path.name.split("-")) == 3


class Summary:
    """One summary folder inside a workspace. CSVs are read lazily on first access."""

    def __init__(self, summary_path: Path, ws_name: str):
        self.path = summary_path
        self.name = summary_path.name   # the summary's own name
        self.ws_name = ws_name          # the workspace it belongs to

    def _read(self, *parts: str) -> pd.DataFrame | None:
        f = self.path.joinpath(*parts)
        return pd.read_csv(f) if f.exists() else None

    @property
    def is_valid(self) -> bool:
        """Check if the given path is a valid Nomadic summary."""
        return (
            self.path.is_dir()
            and (self.path / "metadata").is_dir()
            and (self.path / "quality_control").is_dir()
            and (self.path / "seq_inventory").is_dir()
            and (self.path / "variants").is_dir()
        )

    @cached_property
    def master_df(self) -> pd.DataFrame | None:
        return self._read("metadata", "master_metadata.csv")

    @cached_property
    def replicates_df(self) -> pd.DataFrame | None:
        return self._read("quality_control", "replicates_qc.csv")

    @cached_property
    def samples_qc_df(self) -> pd.DataFrame | None:
        return self._read("quality_control", "samples_qc.csv")


class Group:
    """A collaborator group folder (COUNTRY-GROUP-NOMADS_Share)."""

    def __init__(self, folder_path: Path):
        self.path = folder_path
        self.country, self.group, _ = folder_path.name.split("-")
        self.summaries: list[Summary] = []

        ws_dir = self.path / "workspaces"
        if not ws_dir.exists():
            return

        for ws in ws_dir.iterdir():
            if not self._check_valid_workspace(ws):
                continue
            for sum_dir in (ws / "summaries").iterdir():
                summary = Summary(sum_dir, ws.name)
                if summary.is_valid:
                    self.summaries.append(summary)

    def __str__(self):
        return f"Collaborator: {self.group} from {self.country}"

    def __repr__(self):
        return f"Collaborator: {self.group} from {self.country}"

    def _check_valid_workspace(self, path: Path) -> bool:
        """
        Check if the given path is a valid Nomadic workspace.
        A valid workspace contains 'results', 'beds', 'metadata'
        and 'summaries' directories.
        """
        return (
            path.is_dir()
            and (path / "results").is_dir()
            and (path / "beds").is_dir()
            and (path / "metadata").is_dir()
            and (path / "summaries").is_dir()
        )

def get_all_groups_data(folder: Path) -> list[Group]:
    """Load every valid group from a folder that has at least one summary."""
    groups = []
    for path in sorted(folder.iterdir()):
        if not check_if_group_root(path):
            continue

        grp = Group(path)
        
        if not grp.summaries:
            print(f"No summaries identified from {grp.group} in {grp.country}")
            continue
        
        by_ws = defaultdict(list)
        for s in grp.summaries:
            by_ws[s.ws_name].append(s.name)
        for ws_name, names in by_ws.items():
            print(f"Processed data from {grp.group} in {grp.country} for workspace(s) {", ".join(names)}")
            # print(f"   {ws_name} summary identified")
            if len(names) > 1:
                print(f"   WARNING: Multiple summaries in the {ws_name} workspace - data may be duplicated")

        groups.append(grp)
    return groups


def merge_groups_data(source: Path | list[Group], summary_attr: str) -> pd.DataFrame:
    """
    Concatenate one summary DataFrame (e.g. "master_df", "replicates_df",
    "samples_qc_df") across all groups and workspaces.

    `source` can be a folder (groups are loaded for you) or a list of Group
    objects already loaded, which avoids rescanning the folder when you
    merge several attributes.
    """
    groups = get_all_groups_data(source) if isinstance(source, Path) else source

    frames = []
    for g in groups:
        for s in g.summaries:
            df = getattr(s, summary_attr, None)
            if df is None:
                continue
            df = df.assign(country=g.country, group=g.group,workspace=s.ws_name, summary=s.name)
            if "expt_name" in df.columns:
                df["date"] = df["expt_name"].map(extract_date)
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)

    if "date" in merged.columns:
        missing = merged["date"].isna().sum()
        if missing:
            print(f"Warning: could not extract a date for {missing} row(s)")
    return merged