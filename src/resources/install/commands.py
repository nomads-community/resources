import logging
from pathlib import Path

import click

from resources.lib.general import (
    conda_env_exists,
    create_conda_env_from_file,
    get_repository_dict,
    git_clone,
    list_repository_details,
    pip_install_in_env,
)
from resources.lib.logging import divider, identify_cli_command

script_dir = Path(__file__).parent.resolve()


@click.command(short_help="Install NOMADS tool(s)")
@click.option(
    "-n",
    "--name",
    type=str,
    required=False,
    multiple=True,
    help="Name of the NOMADS tool to install. If installing multiple tools add multiple -n flags",
)
@click.option(
    "-l",
    "--list_tools",
    is_flag=True,
    help="List all NOMADS tool names and info",
)
@click.option(
    "-g",
    "--git_folder",
    type=Path,
    required=False,
    default=Path.home() / "git",
    help="Path to git folder to store all repositories",
)
def install(name: str, git_folder: Path, list_tools: bool):
    """Install NOMADS tool(s)"""

    # Set up child log
    log = logging.getLogger("install_commands")
    log.info(divider)
    log.debug(identify_cli_command())

    # Load repo information from YAML file
    repos_dt = get_repository_dict()

    if list_tools:
        # List repos and exit
        list_repository_details(list_tools, repos_dt)

    if not name:
        raise ValueError(
            "Please specify a NOMADS tool tool name to install. List all available with -l flag"
        )

    for repo in name:
        repo = repo.lower()
        log.info(f"Attempting to install environment {repo}")

        if repo not in repos_dt:
            log.info(f"{repo} is not a valid NOMADS tool name.")
            log.info(divider)
            list_repository_details(list_tools, repos_dt)
        git_target = git_folder / repo
        git_dt = repos_dt.get(repo)
        git_url = git_dt.get("url")

        # Ensure cloned
        if not git_target.exists():
            git_clone(git_url, git_target)
        else:
            log.info(f"   {repo} folder present in {git_folder}")

        # Check if it should have its own conda env
        if not git_dt.get("conda", False):
            log.info(f"   {repo} does not require a conda environment. Skipping...")
            log.info(divider)
            continue

        # Install environment
        if conda_env_exists(repo):
            log.info(f"   {repo} environment found. Skipping...")
            log.info(divider)
            continue
        log.info(f"   installing {repo}")
        created = create_conda_env_from_file(git_target)
        if not created:
            log.info(f"Error creating environment {repo}")
            log.info(divider)
            continue

        # Install local variables
        if not git_dt.get("pip", False):
            log.info(divider)
            continue
        pip_install_in_env(repo, git_target)
        log.info(divider)
