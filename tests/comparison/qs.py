#!/usr/bin/env python3

from json import dumps, loads
from os.path import dirname, join, realpath

from qs_codec import decode, encode


def main():
    # Get the directory of the current script
    script_dir = dirname(realpath(__file__))

    # Construct the path to the JSON file
    file_path = join(script_dir, "test_cases.json")

    # Read the JSON file
    with open(file_path, "r") as file:
        contents = file.read()

    # Parse the JSON contents into a list of dictionaries
    e2e_test_cases = loads(contents)

    # Iterate over the test cases
    for test_case in e2e_test_cases:
        # Encode the 'data' field
        encoded = encode(test_case["data"])
        # Decode the 'encoded' field
        decoded = decode(test_case["encoded"])
        # Print the results
        print("Encoded:", encoded)
        print("Decoded:", dumps(decoded, separators=(",", ":")))


if __name__ == "__main__":
    main()
