#!/bin/bash
FUZZING_TIMES=${1:-10}
ATHERIS_RUNS=${2:-1000}
# coverage erase

for ((i=0; i<FUZZING_TIMES;))
do
    times=$((++i))
    echo "The ${times} time(s):"
    echo "Waiting..."

    TARGET_SECOND=1
    CURRENT_SECOND=$(date "+%S")
    SLEEP_TIME=$((60 - 10#$CURRENT_SECOND + TARGET_SECOND))
    sleep ${SLEEP_TIME}

    FOLDER=$(date "+database/Log/%Y%m%d_%H%M")
    mkdir -p "$FOLDER"
    python -m coverage run --append fuzzing.py -atheris_runs=$ATHERIS_RUNS 2> "$FOLDER/output.txt"
    echo "----------------------------------------"
done
