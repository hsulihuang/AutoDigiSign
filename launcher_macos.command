#!/bin/zsh

scheduled=0
if [[ "${1:-}" == "--scheduled" ]]; then
    scheduled=1
fi

# Always run from the project directory, including when opened from Finder.
project_directory="${0:A:h}"
if ! cd -- "$project_directory"; then
    echo "AutoDigiSign could not open its project directory."
    exit 1
fi

python_executable="$project_directory/.venv/bin/python"
export PYTHONPATH="$project_directory/src"

if [[ ! -x "$python_executable" ]]; then
    echo "Project virtual environment was not found."
    echo "Create it with: python3.14 -m venv .venv"
    echo "Then install the project with: .venv/bin/python -m pip install --editable ."
    exit_code=1
else
    echo "Running AutoDigiSign..."
    "$python_executable" -m autodigisign
    exit_code=$?
fi

if (( exit_code == 0 )); then
    echo "AutoDigiSign completed successfully."
else
    echo "AutoDigiSign failed with exit code $exit_code."
fi

if (( scheduled == 0 )); then
    if (( exit_code == 0 )); then
        echo "This launcher will exit in 10 seconds."
        sleep 10
    else
        echo "Press any key to close this launcher."
        read -rs -k 1
        echo
    fi
fi

exit "$exit_code"
