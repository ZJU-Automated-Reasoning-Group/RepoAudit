#!/bin/bash

python3 repoaudit.py \
  --language Java \
  --model-name claude-3.7 \
  --project-path ../benchmark/Java/toy/NPD \
  --bug-type NPD \
  --is-reachable \
  --temperature 0.0 \
  --scan-type dfbscan \
  --call-depth 6 \
  --max-workers 3