from pathlib import Path

import click

from resources.lib.general import (
    change_git_URL,
    get_repository_dict,
    git_pull,
    pip_install_in_env,
)


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

    if not git_folder.exists():
        raise FileNotFoundError(f"Directory {git_folder} does not exist.")

    # Load repo information from YAML file
    repos_dt = get_repository_dict()

    # Identify all git folders
    for subdir in git_folder.iterdir():
        if subdir.name not in repos_dt or subdir.name.startswith("."):
            continue
        print(f"Identified {subdir.name} repo...")

        # Change URL if specified
        if url_type:
            if url_type not in ["https", "ssh"]:
                raise ValueError("URL type must be either https or ssh")
            change_git_URL(url_type, subdir)

        # Perform a git pull
        _, updated = git_pull(subdir)
        if not updated:
            continue

        # Install local variables with pip if needed
        if not repos_dt.get(subdir.name).get("pip", False):
            continue
        pip_install_in_env(subdir.name, subdir)


if __name__ == "__main__":
    update()
