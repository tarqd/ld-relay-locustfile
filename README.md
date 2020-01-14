# LD-Relay Locust File

This is a locust file meant to emulate the load of launchdarkly server and mobile clients.


# Setup

- Create a flag with the key `locust-heartbeat` with the type number with two variations
- Create an api key that can modify this flag 
- Update the task sets to emulate kind of load you expect
- Set the `LAUNCHDARKLY_MOBILE_KEY` and `LAUNCHDARKLY_SDK_KEY` to the keys for your project
- Set `LAUNCHDARKLY_HEARTBEAT_PROJECT` to the project key of your project
- Set `LAUNCHDARKLY_HEARTBEAT_API_KEY` to the api key you generated
- Run locust with `python -m locust -f locustfile.py
- Open `https://localhost:8089` and enter your desired users and set the host to your instance of LD-Relay




# Locust Api Token Policy

Below is an inline policy that would allow the token you generate to update the `locust-heartbeat` flag in any of your projects

```
[
  {
    "resources": [
      "proj/*:env/*:flag/locust-heartbeat"
    ],
    "actions": [
      "updateFlagVariations"
    ],
    "effect": "allow"
  }
]
```