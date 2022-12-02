#!/bin/bash

### Make sure there are environment variables for umls username and password
#if [ -z $umls_api_key ] ; then
#   echo "Environment variable umls_api_key must be defined"
#   exit 1
#fi

export ctakes_umlspw=#enter your key here

export ctakes_umlsuser=umls_api_key

## Pass in environment variables
docker run -p 8080:8080 --rm -e ctakes_umlsuser -e ctakes_umlspw -d ctakes-covid 
