#!/bin/bash
# NOMADS repos update script
# Written by Daniel Bridges (dbscientificltd@gmail.com)

#Generate the necessary for
condabase="$(conda info --all | grep "base environment" | sed s/"base environment : "// | sed s/\(writable\)// | sed s/\s+//)"
condapath="/etc/profile.d/conda.sh"
condash=$(echo $condabase$condapath | sed s/[[:space:]]//)

divider="\n\n***************************************\n"

function change_conda {
    #source the conda executable
    echo "Changing from $CONDA_DEFAULT_ENV env to $1."
    source $condash
    conda activate $1
    echo "   $CONDA_DEFAULT_ENV"
    if [[ $CONDA_DEFAULT_ENV != $1 ]]; then
        echo "Failed to enter correct conda env"
        exit
    fi
}

function change_git_origin_between_https_ssh {
    # Validate input argument
    if [[ ! "$1" =~ ^(https|ssh)$ ]]; then
        echo "Error: Invalid argument. Please provide 'https' or 'ssh'."
        return 1
    fi

    CURRENT=$(git remote get-url origin | awk -F'[://@]' '{print $1}' | sed s/git/ssh/)
    GITSTUB=$(git remote get-url origin | sed 's/https:\/\/github.com\///' | sed 's/git@github.com://' | sed 's/https:\/\/github.com\///' | sed 's/git@github.com://')

    #Remove those that match
    if [[ "$CURRENT" = "$1" ]]; then
        return
    fi

    #Change as required
    if [[ "$1" = "https" ]]; then
        echo "   Changing to https origin"
        git remote set-url origin https://github.com/$GITSTUB
    elif [[ "$1" = "ssh" ]]; then
        echo "   Changing to ssh origin"
        git remote set-url origin git@github.com:$GITSTUB
    else
        echo "unknown git origin "
    fi

}

# Define directory holding the git repos
git_dir="$HOME/git/"

# Parse command-line arguments
while getopts ":g:o" opt; do
    case $opt in
    o) change_origin=true ;;
    g) git_dir="$OPTARG" ;;
    \?)
        echo "Invalid option: -$OPTARG" >&2
        exit 1
        ;;
    esac
done

# Shift away processed options from remaining arguments
shift $((OPTIND - 1))

echo "Searching $gitdir for git folders:"
printf $divider

#Identify all likely dir in the git_dir
find "$git_dir" -mindepth 1 -maxdepth 1 -type d -not -path '*/.*' | while read dir; do

    #test if it is a git repo
    if ! [[ -d "$dir/.git" ]]; then
        continue
    fi

    repo=$(basename "$dir")
    echo "Found $repo. Attempting to update:"
    cd $dir

    #Ensure that it is using an https
    if [[ $change_origin = "true" ]]; then
        change_git_origin_between_https_ssh https
    fi

    output=$(git pull)
    status=$?
    # Highlight those that failed
    if ! [[ $status -eq 0 ]]; then
        echo "   ERROR: Git pull failed."
        echo "      $output"
        printf $divider
        continue
    fi

    #Finish with those that are up to date
    if [[ "$output" == "Already up to date." ]]; then
        echo "   $output"
        printf $divider
        continue
    fi

    # Check if there is a README file
    readme="README.md"
    if [ ! -f $readme ]; then
        echo "   Error: File 'README.md' does not exist."
        exit 1
    fi

    #Search for install phrase
    phrase="pip install -e ."
    if ! grep -q "$phrase" "$readme"; then
        echo "   No pip install required"
        printf $divider
        continue
    fi

    #Check environment exists
    env_present=$(conda info --envs | grep warehouse | wc -l)
    if [[ $env_present -eq "1" ]]; then
        #Change into the env
        change_conda "$repo"
        pip install -e .
        printf $divider
    else
        echo "   $repo not installed. Please install and then re-run this script"
    fi

    printf $divider
done
