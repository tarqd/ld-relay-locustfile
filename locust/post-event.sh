#!/bin/bash

curl -vvv -H "Authorization: $LAUNCHDARKLY_SDK_KEY" -H "X-LaunchDarkly-Event-Schema: 3" -H "Content-Type: application/json"  -H "User-Agent: PythonClient/6.11.3" -H "Accept: application/json" -d @- "$@"

