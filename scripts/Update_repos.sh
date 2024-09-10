#!/bin/bash


function change_conda {
    #Use absolute path in case being run in crontab
    source $HOME/.miniforge/etc/profile.d/conda.sh
#     set +eu
    conda activate $1
}


# Define directory holding the git repos
git_dir="$HOME/Desktop/git/"

#Identify all likely dir in the git_dir
find "$git_dir" -mindepth 1 -maxdepth 1 -type d -not -path '*/.*' | while read dir; do
    #test if it is a git repo
    if ! [[ -d "$dir/.git" ]]; then
        continue
    fi

    repo=$(basename "$dir")
    echo "Attempting to update $repo"
    cd $dir

    output=$(git pull)
    status=$?

    # Highlight those that failed
    if ! [[ $status -eq 0 ]]; then
        echo "Git pull failed."
        echo "   $output"
        continue
    fi

    #Finish with those that are up to date
    if [[ "$output" == "Alreadyup to date." ]]; then
        echo "   $output"
        continue
    fi

    # Check if there is a README file
    readme="README.md"
    if [ ! -f $readme ]; then
        echo "Error: File 'README.md' does not exist."
        exit 1
    fi

    #Search for install phrase
    phrase="pip install -e ."
    if ! grep -q "$phrase" "$readme"; then
        echo "No pip install required"
        continue
    fi
    #Check environment exists
    env_present=`conda info --envs | grep warehouse | wc -l`
    if [[ $env_present -eq "1" ]]; then
        #Change into the env
        change_conda "$repo"
        $repo --version
        # Execute the pip command (assuming you have pip installed)
        pip install -e .
    else
        echo "$repo not installed. Please install and then re-run this script"
    fi


done
