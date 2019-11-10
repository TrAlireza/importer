#!/bin/bash

if [[ "$1" = *".py" ]]; then
    PYTHONPATH=.:./lib exec python $@
    exit $?
fi

if [[ "$1" = "python"* ]]; then
    shift
    PYTHONPATH=.:./lib exec python $@
    exit $?
fi
