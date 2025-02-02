#!/usr/bin/env bash
# This script will upload the contents of the local _html folder
# to my web server.
#
# Any arguments passed to this script will be passed to the underlying
# rsync command.

set -o errexit
set -o nounset
set -o xtrace

rsync \
  --compress \
  --archive \
  --recursive \
  --delete \
  --verbose \
  --include="" \
  --filter="" \
  "_html/" \
  "alexwlchan@alexwlchan.net:repos/alexwlchan.net/_site/my-tools/library-lookup/" \
  "$@"
