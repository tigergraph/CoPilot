To run: 

Add a `config.json` with the following format
```json
{
    "copilotURL": "http://localhost:8000",
    "VuCount": 10,
    "duration": "3m",
    "username": "tigergraph",
    "password": "tigergraph",
    "graphName": "DigitalInfra"
}
```

Then, exec `./run.sh`. You don't need to install k6, `run.sh` will do that for you. If you pass an argument to `run.sh`, the html output will be written to a file
with that name.

