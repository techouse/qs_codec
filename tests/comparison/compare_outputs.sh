#!/usr/bin/env bash

# Get the directory of the script
script_dir=$(dirname "$0")

# Run the JavaScript and Python scripts and save their outputs
node_output=$(node "$script_dir/qs.js")
python_output=$(python3 "$script_dir/qs.py")

# Compare the outputs
if [ "$node_output" == "$python_output" ]; then
    echo "The outputs are identical."
    exit 0
else
    echo "The outputs are different."
    exit 1
fi
