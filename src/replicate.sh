#!/bin/bash

cd "$(dirname "$0")"
if [ ! -d ../log ]; then
    mkdir ../log
fi
../venv/bin/python replicate.py
