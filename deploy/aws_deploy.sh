#!/bin/bash
#pip install python-lambda -U
lambda deploy \
  --config-file aws_config.yaml \
  --requirements requirements.txt