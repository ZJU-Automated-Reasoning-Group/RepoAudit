#!/bin/bash
SCAN_TYPE=$1
LANGUAGE=Java
MODEL=glm-4-flash
BUG_TYPE=NPD
PROJECT=toy

# For demo/test run
python3 repoaudit.py \
  --language $LANGUAGE \
  --model-name $MODEL \
  --project-path ../benchmark/${LANGUAGE}/${PROJECT} \
  --bug-type $BUG_TYPE \
  --is-reachable \
  --temperature 0.0 \
  --scan-type dfbscan \
  --call-depth 3 \
  --max-neural-workers 30


# --scan-type inconsistency \
