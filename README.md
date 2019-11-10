# Importer

This module loads data via an external API endpoint (Mailchimp) and writes the results after a transformation of data via another external API endpoint (Ometria).

State is kept in a json file that is updated with every successful iteration.

Once the importer is running, it checks the state file every minute and if a refresh is required it will schedule it. 

It is safe to update the state file during this time:
```
2019-10-21 10:51:16 INFO |main|go|155| controller: starting...
2019-10-21 10:51:16 INFO |main|go|165| controller: checking all lists.
2019-10-21 10:51:16 INFO |main|go|186| controller: list "1a2d7ebf82" up to date, last updated on "2019-10-21 09:50:54".
2019-10-21 10:51:16 INFO |main|go|186| controller: list "1a2d7ebf82" up to date, last updated on "2019-10-21 09:51:05".
2019-10-21 10:51:16 INFO |main|go|188| controller: sleeping for 60 seconds.
```
 

## TL;DR
Start in the base directoy (after unpacking the 
zip/tar or cloning the repository).

```
$ chmod 755 run.sh
$ ls -l state
total 8
-rw-r--r--  1 <###>  staff  306 17 Oct 13:27 state.json
$ ./run.sh build && ./run.sh test && run.sh go
```

Now, the "stats.json" file in the "state" directory can be manually updated to force the update or reload of the corresponding list.

To stop the importer press "ctrl+C" or type the following in
another terminal:
```bash
$ touch state/controller.quit
```

## State file
State file "state.json" is in the "state" directory, is 
in json format and **_can be
changed manually while the importer is running to force 
for example updating the list or fully loading it up 
by changing the latest_timestamp to a 
value more than 2 hours in the past or "null" respectively_**.

Note: "run.sh" will map the local "state" directory containing "state.json" 
to "/opt/ometria/state" inside Docker to allow preserving the 
state between subsequent runs.

State is an array of object each of which 
represents a list for example:
```json
[
  {
    "list_id": "1a2d7ebf82",
    "latest_timestamp": "2019-10-18T22:20:23",
    "start_offset": 10000,
    "items_per_request": 250,
    "worker_count": 4,
    "elapsed_seconds": 1.6,
    "total_updates": 10133
  }
]
```

The same list (ie. same "list_id") could be presented in two (or more) objects
perhaps to have different parameters:
```json
[
  {
    "list_id": "1a2d7ebf82",
    "latest_timestamp": "2019-10-18T22:20:23",
    "elapsed_seconds": 1.6
  },
  {
    "list_id": "1a2d7ebf82",
    "latest_timestamp": "2019-10-18T22:20:23",
    "start_offset": 10000,
    "items_per_request": 500,
    "worker_count": 6,
    "elapsed_seconds": 1.6
  }
]
```

The only required field in the object is "list_id". All the 
other fields have their own defaults. So the following entry:
```json
[
  {
    "list_id": "1a2d7ebf82"
  }
]
```

will be updated to the following after the first iteration 
of the importer that is a full load of list since 
there is no timestamp:
```json
[
  {
    "list_id": "1a2d7ebf82",
    "latest_timestamp": "2019-10-18T22:20:23",
    "elapsed_seconds": 1.6,
    "total_updates": 46134
  }
]
```

However the defaults are not written to the state 
(unless provided in the state)
meaning the following state is the same 
as the above state:
```json
[
  {
    "list_id": "1a2d7ebf82",
    "latest_timestamp": "2019-10-18T22:20:23",
    "start_offset": 0,
    "items_per_request": 100,
    "worker_count": 8,
    "elapsed_seconds": 1.6,
    "total_updates": 46134
  }
]
```

field | data | default
--- | :--- | ---:
start_offset| where to load the data from (could be set to non-zero which is useful for live testing) | 0
items_per_request| (performance tuning) read and write how many items per http get/post request | 100
worker_count| (performance tuning) the number of asyncio tasks created for reading/writing of data from and to endpoints | 8
latest_timestamp | latest timestamp the list was updated in iso format | json: null
elapsed_seconds | the total elapsed time in seconds for the last sync/load operation |
total_updates | number of records updated during the last sync/load operation | 

## How To?
A Bash file is provided that builds the Docker image
, runs the tests and runs the importer itself. "run.sh" is in 
the base directory and should be executable by Bash.

It also contains the API Keys that are injected to Docker image via the environment variables.

```bash
$ chmod 755 run.sh
```

```bash
$ ./run.sh
# ---
# version: Show Docker Image Version
# build: Build Docker Image
# test: Run tests
# go: Run controller
# ---
```

### Building Docker image
```bash
$ ./run.sh build
```

### Running tests
```bash
$ ./run.sh test
```

### Running the Importer
```bash
$ ./run.sh go
```

### Building and running locally
The requirements.txt is in the base directory to allow building the venv and running the code locally.

```bash
$ python3 -m venv venv
$ . venv/bin/activate
$ pip install -r requirements.txt
$ PYTHONPATH=.:./lib OMETRIA_APIKEY='<api_key>' MAILCHIMP_APIKEY='<api_key>' python importer/main.py
```

## Improvment
Lists are sequentially processed, so in case of more than one list requiring sync-ing they are scheduled one after the other.

In cases that there are many lists in the state file, having the processing scheduled concurrently will speed up the overal time. 

**_The caveat is the level of concurrency acceptable by external API endpoints_**.
