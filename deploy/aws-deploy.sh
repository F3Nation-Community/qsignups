#!/bin/bash
#pip install python-lambda -U
lambda deploy \
  --config-file deploy/aws_config.yaml \
  --requirements requirements.txt