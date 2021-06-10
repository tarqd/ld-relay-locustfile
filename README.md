![screenshot](screenshot.png)


# LD-Relay Locust File


This is a locust file meant to emulate the load of launchdarkly server and mobile clients.


# Setup

## Prerequisites

If you are running the testing infrastructure outside of Docker you will need to install the dependencies. This project utilizes `Python 3`, and `Locust 1.5.3`. You can install the required version of Locust with:

```
pip3 install locust==1.5.3
```

As with many Python projects you will also need to install the dependencies listed in `requirements.txt`. 

```
pip3 install -r locust/requirements.txt
```


## Optional: Configure a flag heartbeat

This will allow you gather metrics on how long it takes for a flag to propogate to clients. If you do not follow these steps, you will not get these metrics in Locust but the tests will still run.

- Create a flag with the key `locust-heartbeat` with the type number with two variations
- Create an api key that can modify this flag (see the example token policy below)


## Modify locustfile.py

First off, take a look at `locust/launchdarkly_locust.py`, this file defines the `LaunchDarklySDKUser` and `LaunchDarklyMobileSDKUser` classes that you will be basing your locusts on.

Now open up `locust/locustfile.py`. You'll see a couple of task sets and locusts that you can modify. Simply edit the task sets to emulate the behavior of your users. The example ones just initialize the client and evaluate random flags.

If you want to modify the client settings, just set the properties you'd normally pass to `LDClient.Config` as properties on the `LaunchDarklyBasicServer` and `LaunchDarklyBasicMobile` classes.

Feel free to create as many new task sets and locust subclasses as you want to define different classes of users and behavior. You can define what percentage of users will use each behavior using the `weight` property on the locust class or task sets.

For more information, [read this guide](https://docs.locust.io/en/stable/writing-a-locustfile.html)


## Setup your environment variables

Configure your environment variables like so:

```
LD_SDK_KEY=sdk-xxx
LD_MOBILE_KEY=mob-xxx
LD_PROJECT_KEY=my-project
LD_API_KEY=${LD_API_KEY}
LOCUST_HOST=http://ldrelay:8030
```

You can also set the `sdk_key` properties on each locust class instead:

```python

class MyLocust(LaunchDarklyMobileSDKUser):
  sdk_key="mob-xxx"
  # or use a different environment variable
  sdk_key=os.environ.get('SOME_OTHER_ENV')
```


## Running the tests

- Run locust with `python3 -m locust -f locustfile.py`
- Open `https://localhost:8089` and enter your desired users and set the host to your instance of LD-Relay

## Running in Docker

```
docker build -t locust-ld-relay .
docker run -p 8089:8089/tcp -e LOCUST_HOST=http://ldrelay:8030 --env-file=env locust-ld-relay:latest
```

## Locally testing with Docker compose

A simple `docker-compose.yml` is provided for local testing. This is the quickest way to get started, however it will not likely be wholly representative of your infrastructure. To get started set the required environment variables `LD_SDK_KEY`, and `LD_MOBILE_KEY`. The variables `LD_PROJECT_KEY`, and ` LD_API_KEY` are supported but optional.

Once your environment is configured run `docker-compose up`, and connect to `http://localhost:8089` in your browser.

## Running in Distributed mode

You can test with large amounts of users by using multiple locust nodes. Simply configure the masters and workers with the following env variables:

### Master

```
LOCUST_MODE=master
```

Be sure to expose port 5557-55578 to your worker nodes

### Workers

```
LOCUST_MODE=worker
LOCUST_MASTER_HOST=<hostname of master>
```

For more information, refer to [Locust Documentation](https://docs.locust.io/en/stable/running-locust-docker.html)


## FAQ

### Why is the RPS so low?

Users don't equate to requests in Locust. The number of users is the number of instances of the Locust classes defined in your locustfile. It will make as many requests as they make while running.


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
