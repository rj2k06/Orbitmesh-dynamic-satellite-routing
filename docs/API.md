# OrbitMesh REST API

Base URL: `http://127.0.0.1:5000/api`

The backend must be running locally before making these requests. JSON request bodies should use `Content-Type: application/json`.

## Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Check backend status |
| `GET` | `/network` | Return current nodes, links, events, and simulation state |
| `GET` | `/algorithms` | Return algorithm metadata |
| `POST` | `/reset` | Restore the baseline scenario |
| `POST` | `/route` | Calculate one route |
| `POST` | `/benchmark` | Compare the supported routing methods |
| `POST` | `/event` | Inject a simulated network event |
| `POST` | `/simulate` | Advance the simulation |

## Route request

`POST /route`

```json
{
  "start": "S1",
  "goal": "G2",
  "algorithm": "dijkstra",
  "weights": {
    "latency": 0.5,
    "congestion": 0.3,
    "energy": 0.2
  }
}
```

Supported algorithm keys: `dijkstra`, `astar`, `bellman`, `floyd`, `genetic`.

## Benchmark request

`POST /benchmark`

Send the same source, destination, and weights fields as the route request. The benchmark evaluates the methods on the current graph.

## Event request

`POST /event`

```json
{ "type": "fail_satellite" }
```

Supported event types: `fail_satellite`, `fail_link`, `weather`, `congestion`, `recover`.

## Simulation request

`POST /simulate`

```json
{ "ticks": 1 }
```

The simulation is synthetic and local; it does not use live orbital data.
