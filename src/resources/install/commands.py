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

script_dir = Path(__file__).parent.resolve()


@click.command(short_help="Select and install NOMADS tools / repositories.")
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
    """Select and install NOMADS tools / repositories."""

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
        if repo not in repos_dt:
            print(f"{repo} is not a valid NOMADS tool name.")
            print("")
            list_repository_details(list_tools, repos_dt)
        git_target = git_folder / repo
        git_dt = repos_dt.get(repo)
        git_url = git_dt.get("url")

        # Ensure cloned
        if not git_target.exists():
            git_clone(git_url, git_target)
        else:
            print(f"{repo} folder present in {git_folder}")

        # Check if it should have its own conda env
        if not git_dt.get("conda", False):
            print(f"{repo} does not require a conda environment. Skipping...")
            continue

        # Install environment
        if conda_env_exists(repo):
            print(f"{repo} environment found. Skipping...")
            continue
        print(f"Attempting to install environment {repo}")
        created = create_conda_env_from_file(git_target)
        if not created:
            print(f"Error creating environment {repo}")
            continue

        # Install local variables
        if not git_dt.get("pip", False):
            continue
        pip_install_in_env(repo, git_target)
