import pandas as pd
from workspace import Workspace

def is_polygenomic(ws: Workspace):
    """Opens the diversity file from a workspace and returns a set of sample_ids that are polygenomic (i.e. have mixed calls)"""
    diversity_df = pd.read_csv(ws.summaries_path / "variants" / "aa_changes.diversity.csv" )
    return set(diversity_df["sample_id"][diversity_df["aa_call"] == "mixed"])