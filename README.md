<p align="center"><img src="misc/nomads_logo.png" width="500"></p>

# Resources
This repository contains a collection of resources to support NOMADS assay implementation including installing and maintaining NOMADS software.

# Bed files
In this folder are the bed files that relate to the various NOMADS assays. 

# Protocol
All published NOMADS protocols, and relevent ONT protocols are listed here.


# Commodities
To assist users in calculating the quantities of each item needed for running a certain amount of samples in a specific NOMADS assay a spreadsheet is provided with internal instructions. Primer sequences are also defined.

# NOMADS Software
## Keeping up to date
Each NOMADS repository can be individually updated using `git pull` and `conda` updates etc, however this can be tedious for multiple repositories. To that end there is a script in the `scripts` subfolder that will attempt to update all installed repositories, by running the following command from your `home` or `git` directory
```
user@computer:~$ ./git/resources/scripts/update_repos.sh
```
