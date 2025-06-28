import os
import re
import shutil
from pathlib import Path

import click


@click.command(
    short_help="Move or link data from shared GDrive folder to the nomadic results folder for local viewing"
)
@click.option(
    "-g",
    "--shared_gdrive_path",
    type=Path,
    required=False,
    help="Path to the GDrive shared sequence data folder",
)
def nomadic(shared_gdrive_path: Path) -> None:
    """
    Move or link data from shared GDrive folder to the nomadic results folder for local viewing
    """

    if not shared_gdrive_path.exists():
        msg = f"Directory {shared_gdrive_path} does not exist. Creating...."
        raise FileNotFoundError(msg)

    home_path = Path.home()
    nomadic_git = home_path / "git" / "nomadic" / "results"

    if not nomadic_git.exists():
        print(f"Nomadic results folder {nomadic_git} does not exist. Creating...")
        nomadic_git.mkdir(parents=True, exist_ok=True)

    # Create symbolic link or copy each set of nomadic results
    for folder_path in shared_gdrive_path.iterdir():
        # Identify if there is nomadic data
        nomadic_results = folder_path / "nomadic"
        if not nomadic_results.exists():
            continue

        # Identify exptid to buil the link
        expt_id = identify_exptid_from_path(nomadic_results, raise_error=False)
        if expt_id:
            target = nomadic_git / expt_id
        else:
            target = nomadic_git / folder_path.name

        # windows needs admin privileges to create symlinks
        if os.name == "nt":
            print(f"Copying nomadic files to {target}...")
            shutil.copytree(nomadic_results, target)
        else:
            print(f"Creating symbolic link for {nomadic_results} to {target.name}...")
            target.symlink_to(nomadic_results, target_is_directory=True)


def identify_exptid_from_path(path: Path, raise_error: bool = True) -> str:
    """
    Extract the experimental ID from a file or folder

    Args:
        path (Path): path to the folder

    Returns:
        expt_id (str): the extracted experiment id or None if not found
    """
    NOMADS_EXPID = re.compile(r"(SW|PC|SL)[a-zA-Z]{2}[0-9]{3}")
    try:
        # First try with the
        match = re.search(NOMADS_EXPID, path.name)
        if match is None:
            # Second try with the full path
            match = re.search(NOMADS_EXPID, str(path))
        if match is None:
            if raise_error:
                raise ValueError(f"Unable to identify an ExpID in: {path}")
            return None

        return match.group(0)

    except StopIteration:
        msg = f"Unable to identify an ExpID in: {path.name}"
        raise ValueError(msg)
