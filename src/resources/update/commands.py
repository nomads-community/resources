import logging
from pathlib import Path

import click

from resources.lib.general import (
    change_git_URL,
    get_repository_dict,
    git_pull,
    pip_install_in_env,
)
from resources.lib.logging import divider, identify_cli_command

# Get logging process
log = logging.getLogger("update")


@click.command(short_help="Update installed NOMADS tool(s)")
@click.option(
    "-g",
    "--git_folder",
    type=Path,
    required=False,
    default=Path.home() / "git",
    help="Path to folder containing repositories.",
)
@click.option(
    "-u",
    "--url_type",
    type=str,
    required=False,
    help="URL type: https or ssh",
)
def update(git_folder: Path, url_type: str = None) -> None:
    """Updates NOMADS tools including installing environment variables."""

    # Set up child log
    log = logging.getLogger("update_commands")
    log.info(divider)
    log.debug(identify_cli_command())

    if not git_folder.exists():
        msg = f"Directory {git_folder} does not exist."
        log.info(msg)
        raise FileNotFoundError(msg)

    # Load repo information from YAML file
    repos_dt = get_repository_dict()

    # Identify all git folders
    for subdir in git_folder.iterdir():
        if subdir.name not in repos_dt or subdir.name.startswith("."):
            continue
        log.info(f"Identified {subdir.name} repo...")

        # Change URL if specified
        if url_type:
            if url_type not in ["https", "ssh"]:
                msg = "URL type must be either https or ssh"
                log.info(msg)
                raise ValueError(msg)
            url_changed = change_git_URL(url_type, subdir)
            if not url_changed:
                log.info(divider)
                continue

        # Perform a git pull
        _, updated = git_pull(subdir)
        if not updated:
            log.info(divider)
            continue

        # Install local variables with pip if needed
        if not repos_dt.get(subdir.name).get("pip", False):
            continue
        pip_install_in_env(subdir.name, subdir)
        log.info(divider)


if __name__ == "__main__":
    update()
