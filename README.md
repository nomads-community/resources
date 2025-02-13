<p align="center"><img src="misc/nomads_logo.png" width="500"></p>

# NOMADS Resources 
This repository contains a collection of resources to support NOMADS assay implementation as well as a tool called `resources` for easy installation and maintainence of NOMADS software.

# Folders

- **bed files:** bed files related to the various NOMADS assays
- **commodities:** information on equipment needed, primer sequences and reagents needed to start NOMADS sequencing
- **misc:** other resources for NOMADS sequencing e.g. a guide to installing on Windows
- **protocol:** all published NOMADS protocols, and relevent ONT protocols


# Resources tool
Each NOMADS repository can be individually installed and updated using various comands, however this can be tedious for multiple repositories. To that end the `resources` tool aims to make it easy to install all other NOMADS tools and update / maintain already installed ones. 

## Installation
<details>

#### Requirements

To install `resources`, you will need:
- Version control software [git](https://github.com/git-guides/install-git)
- Package manager [mamba](https://github.com/conda-forge/miniforge) 

**1. Clone the repository from github:**
```
git clone https://github.com/nomads-community/resources.git
cd resources
```

**2. Install the dependencies with mamba:**
```
mamba env create -f environments/run.yml
```

**3. Open the `resources` environment:**
```
mamba activate resources
```
**4. Install `resources` and remaining dependencies:**
```
pip install -e .
```
</details>

## Basic usage
<details>

`resources` has two commands which can be viewed by typing `resources --help`:
```
Usage: resources [OPTIONS] COMMAND [ARGS]...

  Install and maintain NOMADS software tools

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  install  Install NOMADS tool(s)
  update   Update installed NOMADS tool(s)
```
Help on each command can be viewed with the --help command e.g. `resources install --help`:
```
Usage: resources install [OPTIONS]

  Install NOMADS tool(s)

Options:
  -n, --name TEXT        Name of the NOMADS tool to install. If installing
                         multiple tools add multiple -n flags
  -l, --list_tools       List all NOMADS tool names and info
  -g, --git_folder PATH  Path to git folder to store all repositories
  --help                 Show this message and exit.
```
</details>

## Acknowledgements
This work was funded by the Bill and Melinda Gates Foundation (INV-003660, INV-048316).