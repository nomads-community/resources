<p align="center"><img src="info/nomads_logo.png" width="500"></p>

# Overview 
This repository contains a collection of resources to support NOMADS assay implementation, you can read more about NOMADS [here](info/NOMADS_introduction.pdf).

# Folders

- **beds**: bed files related to the various NOMADS assays ([nomadic](https://jasonahendry.github.io/nomadic/) will be the most up to date).
- **info**:  Checklists for planning to implement NOMADS assays and guides to installing / using software 
- **notebooks**: Interactive python notebooks to allow downstream analysis of `nomadic` generated data. These notebooks augment rather than replace the `nomadic dashboard` and give the user the freedom to slice, dice and visualise the data however a user chooses to.
- **protocols**: NOMADS and ONT manufacturer protocols for implementation

## notebooks
Ensure the environment is installed and you can access the jupyter lab interface in your browser. Notebooks are sorted into folders so explore the folders and the notebooks available.

# Installation
Clone the github repository

```
git clone https://github.com/nomads-community/resources.git
```

Open the cloned repository, create, and then activate the environment

```
cd resources
conda env create -f environments/nomads.yml
conda activate nomads
```

Open the interactive environment that will appear in your web browser
```
jupyter lab
```

Navigate to the notebooks folder. Duplicate the example_config.yaml, rename it to config.yaml and edit its contents to point to your data.


## Acknowledgements
This work was funded by the Bill and Melinda Gates Foundation (INV-003660, INV-048316).