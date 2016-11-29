#!/bin/bash

SRC_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

REMOTE_HOST=taurus-mgmt
REMOTE_DIR='$HOME/interference'

FILES=

##########################################
find .  \( -path ./.git -o -path './build*' -o -path './install*' -o -path ./install -o -name '*~' \) -prune -o -type f -print0 |
    rsync -avz --files-from=- --from0 ./ $REMOTE_HOST:$REMOTE_DIR
