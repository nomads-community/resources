import subprocess
from pathlib import Path

import click


def change_git_URL(url_to_change_to: str, repo_path: Path) -> bool:
    """
    Change the origin URL of a git repository to either HTTPS or SSH.

    Args:
        url_type: The new URL type (https or ssh).
        repo_path: The path to the git repository.

    Returns:
        bool: True if the URL was successfully changed, False otherwise.
    """
    # First get the current git URL
    current_url = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if not current_url.returncode == 0:
        print(f"Failed to get URL for {repo_path}.")
        return False

    url = current_url.stdout.strip()
    # Identify URL type and the opposite version
    if url.startswith("https://"):
        url_type = "https"
        opposite_url = url.replace("https://", "git@")
        opposite_url = opposite_url.replace("/", ":", 1)  # Replace first / with :
    elif url.startswith("git@"):
        url_type = "ssh"
        opposite_url = url.replace("git@", "https://")
        opposite_url = opposite_url.replace(".com:", ".com/")
    else:
        raise ValueError(f"URL {url} is not in a recognised format.")

    if url_type == url_to_change_to:
        print(f"   Already using {url_type} URL.")
        return

    # Update the URL
    try:
        set_url = subprocess.run(
            ["git", "remote", "set-url", "origin", opposite_url],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to change URL for {repo_path}.")
        print(e)
        return False

    print(f"   Converted from {url_type} to {url_to_change_to} URL")
    return True


@click.command(short_help="Update NOMADS git repositories")
@click.option(
    "-g",
    "--git_folder",
    type=Path,
    required=False,
    help="Path to folder containing repositories.",
)
@click.option(
    "-u",
    "--url_type",
    type=str,
    required=False,
    help="URL type: https or ssh",
)
def update_repository(git_folder: Path, url_type: str = None) -> None:
    """Updates NOMADS git repositories including installing environment variables."""
    if not git_folder:
        git_folder = Path.home() / "git"
        print(f"Using default git folder: {git_folder}")
    if not git_folder.exists():
        raise FileNotFoundError(f"Directory {git_folder} does not exist.")

    # Identify all git folders
    for subdir in git_folder.iterdir():
        # Check it is a git repo
        if not (
            subdir.is_dir()
            and (subdir / ".git").exists()
            and not subdir.name.startswith(".")
        ):
            continue

        # Check it is a NOMADS repo
        NOMADS_repos = {
            "nomadic": True,
            "resources": False,
            "bioinfomatics": False,
            "savanna": True,
            "warehouse": True,
        }
        if subdir.name not in NOMADS_repos:
            continue

        print(f"Identified {subdir.name} repo...")

        # Change URL if specified
        if url_type:
            if url_type not in ["https", "ssh"]:
                raise ValueError("URL type must be either https or ssh")
            change_git_URL(url_type, subdir)

        # Perform a git pull
        output = subprocess.run(
            ["git", "pull"], cwd=subdir, capture_output=True, text=True
        )
        # Check if the repo is up to date
        if "already up to date" in output.stdout.lower():
            print("   Already up to date.")
            continue

        # Check if repo should have pip install
        if not NOMADS_repos.get(subdir.name):
            continue
        try:
            install_result = subprocess.run(
                ["conda", "run", "-n", subdir.name, "pip", "install", "-e", "."],
                cwd=subdir,
                capture_output=True,
                text=True,
            )

        except subprocess.CalledProcessError:
            print(f"Failed to install {subdir.name}.")
            continue

        if install_result.returncode != 0:
            print(f"   Failed to install {subdir.name}.")
            print(f"   {install_result.stderr.strip()}")
        else:
            print(f"   Successfully installed {subdir.name}.")


if __name__ == "__main__":
    update_repository()
