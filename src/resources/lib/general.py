import json
import subprocess
import sys
from pathlib import Path

import yaml

resource_dir = Path(__file__).parent.parent.resolve()


def get_repository_dict() -> dict:
    """
    Function to open yaml file containing information on NOMADS repositories and load the contents into a dictionary.
    Returns:
        dict: Dictionary containing repository information.

    """
    yaml_file = resource_dir / "NOMADS_repos.yml"

    with open(yaml_file, "r") as f:
        repos = yaml.safe_load(f)
    if not repos:
        raise ValueError(f"Failed to load repository information from {yaml_file}")
    return repos


def list_repository_details(list_tools, repos) -> None:
    print("Listing all available NOMADS repositories available for installation:")
    print("")
    print("Repository name\t\tDescription")
    print("==============\t\t===========")
    for repo in repos:
        print(f"{repo:<20}\t{repos[repo]['blurb']:<50}")
    exit()


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
        return True

    # Update the URL
    try:
        set_url = subprocess.run(
            ["git", "remote", "set-url", "origin", opposite_url],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        print(f"   Converted from {url_type} to {url_to_change_to} URL")
        print(set_url.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to change URL for {repo_path}.")
        print(e)
        return False


def git_clone(repo_url: str, repo_path: Path) -> bool:
    """Clones a Git repository.

    Args:
        repo_url: The URL of the Git repository.
        repo_path: The directory where the repository should be cloned to.

    Returns:
        True on successful clone, False otherwise
    """

    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                repo_url,
                str(repo_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        print(f"{repo_path.name} successfully cloned.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Git clone failed: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Git command not found. Is Git installed?", file=sys.stderr)
        return False
    except Exception as e:  # Catch other potential errors
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False


def conda_env_exists(env_name: str) -> bool:
    """Checks if a conda environment exists.

    Args:
        env_name: The name of the conda environment to check.

    Returns:
        True if the environment exists, False otherwise.
    """
    mamba = "mamba"
    if sys.platform == "win32":
        mamba = r"C:\ProgramData\miniforge3\scripts\mamba.exe"

    try:
        result = subprocess.run(
            [mamba, "env", "list", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )

        env_list = json.loads(result.stdout)

        for env in env_list["envs"]:
            # Normalize the paths to handle differences in how conda reports them
            env_path = env.replace("\\", "/")  # Windows paths can have backslashes
            print(env_path)
            if (
                env_path.endswith(env_name)
                or env_path.endswith(f"/envs/{env_name}")
                or env_path.endswith(f"\\envs\\{env_name}")
            ):
                return True
        return False

    except subprocess.CalledProcessError as e:
        print(f"Error checking conda environments: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Mamba command not found. Is it installed?", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing mambas output (invalid JSON): {e}", file=sys.stderr)
        print(
            result.stdout if "result" in locals() else "No output to parse",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False


def create_conda_env_from_file(repo_path: Path) -> bool:
    """Creates a conda environment from a YAML file (environments/run.yaml) using mamba.

    Args:
        repo_path: The path where the repo has been cloned to

    Returns:
        True on successful environment creation, False otherwise
    """
    envfile_path = repo_path.joinpath("environments", "run.yml")
    if not envfile_path.exists():
        print(f"Environment file not found: {envfile_path}", file=sys.stderr)
        return False

    mamba = "mamba"
    if sys.platform == "win32":
        mamba_path = r"C:\ProgramData\miniforge3\scripts\mamba.exe"
        if not Path(mamba_path).exists():
            print(f"Mamba not found in: {mamba_path}", file=sys.stderr)
            return False
        mamba = mamba_path

    command = [mamba, "env", "create", "-f", str(envfile_path)]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.PIPE,
        )

        # Use communicate to handle stdin, stdout, and stderr reliably
        stdout, stderr = process.communicate("Y\n")
        # Get return code after communicate
        return_code = process.returncode
        if return_code == 0:
            print("Mamba environment created successfully!")
            if stderr:
                print(f"STDERR (on success): {stderr.strip()}", file=sys.stderr)
            return True
        else:
            print(
                f"Mamba environment creation failed with return code {return_code}",
                file=sys.stderr,
            )
            print(f"STDOUT: {stdout.strip()}", file=sys.stderr)
            print(f"STDERR: {stderr.strip()}", file=sys.stderr)
            return False

    except FileNotFoundError:
        print("Mamba command not found. Is mamba installed?", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False


def pip_install_in_env(env_name: str, repo_path: Path) -> bool:
    """Performs a pip install to identify local variables

    Args:
        env_name: The name of the conda environment to activate.
        repo_path: Folder where the repository has been cloned to

    Returns:
        True on successful activation, False otherwise.
    """

    if not conda_env_exists(env_name):
        create_env = input(
            f"Conda environment '{env_name}' does not exist. Do you want to create it? (y/n): "
        ).lower()
        if create_env != "y":
            print("Environment creation declined. Exiting.", file=sys.stderr)
            return False
        create_conda_env_from_file(repo_path)

    try:
        command = ["conda", "run", "-n", env_name, "pip", "install", "-e", "."]
        shell = sys.platform == "win32"

        result = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            shell=shell,
        )
        print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Conda environment activation failed: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Conda command not found. Is conda installed?", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False


def git_pull(repo_path: Path) -> bool:
    """Performs a git pull in the specified repository.

    Args:
        repo_path: The path the repository has been cloned to.

    Returns:
        True on successful pull, False otherwise. Prints error messages to stderr.
    """
    # Check it is a git repo
    if not repo_path.is_dir():
        print(f"Repository path is not a directory: {repo_path}", file=sys.stderr)
        return False

    # Check not .git directory
    if not (repo_path / ".git").is_dir():
        print(f"Not a Git repository: {repo_path}", file=sys.stderr)
        return False

    try:
        command = ["git", "pull"]
        result = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        print(result.stdout)

        if "Already up to date" in result.stdout:
            return True, False
        else:
            return True, True

    except subprocess.CalledProcessError as e:
        print(f"Git pull failed: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Git command not found. Is Git installed?", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False
