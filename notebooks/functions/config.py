from pathlib import Path

import yaml

with open("../config.yaml") as f:
    config = yaml.safe_load(f)

# Convert user paths
workspace_dir = Path(config["workspace_dir"]).expanduser()
output_dir = Path.cwd() / config["output_dir"]

# Derived paths
summaries_dir = workspace_dir / "summaries" / workspace_dir.name

# Other settings
save_results = config["save_results"]
min_prevalence = config["min_prevalence"]
expts_to_exclude = config["expts_to_exclude"]
categories = config["categories"]
