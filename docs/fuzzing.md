# Fuzzing

This file provides details about how to conduct fuzz testing (fuzzing) of the smart building control protocol implementation in SBCSE.


## Prerequisites

Fuzzing is conducted via the tool named [Atheris](https://github.com/google/atheris), which should be installed first according to the instructions on its page.

In addition, we recommend to install the tool named [Coverage.py](https://coverage.readthedocs.io/en/latest/), which is optional in case you want to visualize code coverage.


## Usage

To start the fuzzing, run the command below:
```
python fuzzing.py
```

Note that no coverage report will be generated if the fuzzer exits due to a crash in native code, or due to libFuzzer's `-runs` option (use `-atheris_runs`). Moreover, if the fuzzer exits via other methods, such as SIGINT (Ctrl+C), Atheris will attempt to generate a report, but may be unable to do so (depending on your code). For consistent reports, we recommend always using the option `-atheris_runs=<number>`.

### Useful options and commands

Some useful command-line options that can be used when fuzzing are as follows:
- `python fuzzing.py -seed=<seed>` will enter a seed
- `python fuzzing.py -atheris_runs=<number>` will set up the number of runs
- `python -m coverage run fuzzing.py ` will generate a coverage data file `.coverage` for visualizing code coverage
- `python -m coverage run --append fuzzing.py` will append the coverage data of this test to that of the previous one

In addition, some commands that can be used for coverage visualization are as follows:
- `coverage report` will report the coverage
- `coverage html` will visualize coverage as HTML format files
- `coverage erase` will delete the `.coverage` file

### Recommended script

In order to automate fuzzing, a script such as that below can be use (note that no seed input is provided).
```
TARGET_SECOND=1
CURRENT_SECOND=$(date "+%S")
SLEEP_TIME=$((60 - 10#$CURRENT_SECOND + TARGET_SECOND))
sleep ${SLEEP_TIME}

FOLDER=$(date "+database/Log/%Y%m%d_%H%M")
mkdir -p "$FOLDER"
python -m coverage run --append fuzzing.py -atheris_runs=1000 2> "$FOLDER/output.txt"
```

Moreover, you can have a look at the script `fuzzing_script.sh` for a more complex example.


## Fuzzing Output 

In order to save the output of the fuzzing, you can redirect the command output to a file using the syntax `2> output.txt`. Some key elements in the output file are explained next:
- Line 1 indicates the fuzzing scenario
- Line 7 shows the seed of that fuzzing scenario 
- The line containing the text "Done xxx in yyy second(s)" records the fuzzing runtime reported by the fuzzer
