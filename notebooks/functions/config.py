from pathlib import Path

import yaml
import sys
import shutil

with open("../config.yaml") as f:
    config = yaml.safe_load(f)

# Convert user paths
workspace_dir = Path(config.get("workspace_dir")).expanduser()
output_dir = Path.cwd() / config.get("output_dir", "results")

# Derived paths
summaries_dir = workspace_dir / "summaries" / workspace_dir.name
results_dir = workspace_dir / "results"

# Other settings
save_results = config.get("save_results",False)
save_format = config.get("save_format","svg")
min_prevalence = config.get("min_prevalence",None)
expts_to_exclude = config.get("expts_to_exclude",None)
categories = config.get("categories",[])
barcodes_to_exclude = config.get("barcodes_to_exclude",None)

def chrome_installed():
    candidates = ["google-chrome", "chromium-browser", "chromium", "google-chrome-stable"]
    found = next((shutil.which(c) for c in candidates if shutil.which(c)), None)
    if found:
        print(f"✓ Chrome/Chromium found at: {found}")
        return True
    print("WARNING: No Chrome/Chromium found. Please install chrome before continuing.", file=sys.stderr)
    return False

def output_config_values_to_user():
    settings = {
        "Workspace dir": workspace_dir,
        "Output dir": output_dir,
        "Summaries dir": summaries_dir,
        "Results dir": results_dir,
        "Save results": save_results,
        "Save format": save_format,
        "Min prevalence": min_prevalence,
        "Experiments excluded": expts_to_exclude,
        "Categories": categories,
        "Barcodes excluded": barcodes_to_exclude,
    }

    print("=" * 40)
    print("Configuration determined from your config.yaml file:")
    print("=" * 40)
    for label, value in settings.items():
        print(f"{label:<22}: {value}")
    print("=" * 40)

    # Only warn about Chrome if the config actually needs it for export
    if save_results:
        chrome_installed()
        print("=" * 40)