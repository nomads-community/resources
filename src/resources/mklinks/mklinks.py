import re
from pathlib import Path

import click


@click.command(short_help="Create symbolic links for nomadic entries")
@click.option(
    "-g",
    "--shared_gdrive_path",
    type=Path,
    required=False,
    help="Path to the GDrive shared sequence data folder",
)
def mklinks(shared_gdrive_path: Path) -> None:
    """Creates symbolic links for nomadic entries in the shared GDrive path."""

    # Set up child log
    # log = logging.getLogger("mklinks")
    # log.info(divider)
    # log.debug(identify_cli_command())

    if not shared_gdrive_path.exists():
        msg = f"Directory {shared_gdrive_path} does not exist. Creating...."
        raise FileNotFoundError(msg)

    home_path = Path.home()
    nomadic_git = home_path / "git" / "nomadic" / "results"

    if not nomadic_git.exists():
        print(f"Nomadic results folder {nomadic_git} does not exist. Creating...")
        nomadic_git.mkdir(parents=True, exist_ok=True)

    # Create symbolic links for each set of results
    for path in shared_gdrive_path.iterdir():
        nomadic_results = path / "nomadic"
        if nomadic_results.exists():
            expt_id = identify_exptid_from_path(nomadic_results, raise_error=False)
            if expt_id:
                target = nomadic_git / expt_id
            else:
                target = nomadic_git / path.name

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
