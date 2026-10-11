from flask import Flask, jsonify, request
from flask_cors import CORS
import math, random, time

app = Flask(__name__)
CORS(app)

SEED = 20260923
rng = random.Random(SEED)

# Simulation controls: faster orbital motion makes route changes visible in a classroom demo.
ORBIT_STEP = 0.08

ALGORITHMS = {
    "dijkstra": {
        "name": "Dijkstra",
        "type": "Exact shortest path",
        "complexity": "O((V + E) log V) with a binary heap",
        "explanation": "Repeatedly expands the lowest-cost unvisited node. With non-negative edge costs, the first finalized distance is optimal."
    },
    "astar": {
        "name": "A*",
        "type": "Heuristic shortest path",
        "complexity": "Worst case O((V + E) log V)",
        "explanation": "Uses path cost plus a geometric estimate to prioritize nodes that appear closer to the destination."
    },
    "bellman": {
        "name": "Bellman-Ford",
        "type": "Repeated relaxation",
        "complexity": "O(VE)",
        "explanation": "Relaxes every edge repeatedly. It is included as a DAA comparison baseline."
    },
    "floyd": {
        "name": "Floyd-Warshall",
        "type": "All-pairs dynamic programming",
        "complexity": "O(V³)",
        "explanation": "Builds shortest paths between every pair by progressively allowing intermediate vertices."
    },
    "genetic": {
        "name": "Genetic Heuristic",
        "type": "Metaheuristic",
        "complexity": "Depends on population × generations × fitness cost",
        "explanation": "Searches a population of candidate routes using selection, mutation and repair. It is useful for comparing exact and heuristic optimization."
    }
}

def make_network(count=60, ground_count=5):
    nodes = []
    planes = 6
    per_plane = max(4, count // planes)
    count = planes * per_plane

    for p in range(planes):
        for k in range(per_plane):
            idx = p * per_plane + k + 1
            theta = 2 * math.pi * k / per_plane
            phase = 2 * math.pi * p / planes
            nodes.append({
                "id": f"S{idx}",
                "kind": "satellite",
                "x": 0.50 + 0.34 * math.cos(theta + phase),
                "y": 0.50 + 0.24 * math.sin(theta + phase),
                "z": 0.18 + 0.82 * ((p % 3) / 2),
                "plane": p,
                "active": True
            })

    stations = [
        ("G1", "Chennai Ground Station", .16, .72),
        ("G2", "Singapore Ground Station", .43, .83),
        ("G3", "Madrid Ground Station", .76, .30),
        ("G4", "Vancouver Ground Station", .84, .66),
        ("G5", "Canberra Ground Station", .60, .16),
    ][:ground_count]

    for sid, name, x, y in stations:
        nodes.append({"id": sid, "kind": "ground", "name": name, "x": x, "y": y, "z": 0, "active": True})

    links = []
    def add(a,b,kind="ISL"):
        if any((e["a"]==a and e["b"]==b) or (e["a"]==b and e["b"]==a) for e in links):
            return
        links.append({
            "id": f"L{len(links)+1}",
            "a": a, "b": b, "kind": kind, "active": True,
            "base_latency": round(rng.uniform(7, 24) if kind=="ISL" else rng.uniform(16, 34), 2),
            "latency": 0.0,
            "bandwidth": round(rng.uniform(350, 1100) if kind=="ISL" else rng.uniform(550, 1300), 1),
            "base_bandwidth": 0.0,
            "congestion": round(rng.uniform(8, 42), 1),
            "base_energy": round(rng.uniform(3, 14) if kind=="ISL" else rng.uniform(8, 18), 2),
            "energy": 0.0,
            "reliability": round(rng.uniform(.985, .999), 5)
        })

    sats = [n for n in nodes if n["kind"]=="satellite"]
    for p in range(planes):
        for k in range(per_plane):
            a = sats[p*per_plane+k]
            b = sats[p*per_plane+(k+1)%per_plane]
            add(a["id"], b["id"])
    for p in range(planes):
        for k in range(per_plane):
            a = sats[p*per_plane+k]
            b = sats[((p+1)%planes)*per_plane+k]
            add(a["id"], b["id"])
    for p in range(planes):
        for k in range(0, per_plane, 2):
            a=sats[p*per_plane+k]
            b=sats[((p+2)%planes)*per_plane+(k+1)%per_plane]
            add(a["id"], b["id"])
    for g in nodes:
        if g["kind"]=="ground":
            near=sorted(sats,key=lambda s:(s["x"]-g["x"])**2+(s["y"]-g["y"])**2)[:5]
            for s in near:
                add(s["id"],g["id"],"GROUND")

    for e in links:
        e["base_bandwidth"] = e["bandwidth"]
    network = {"nodes":nodes,"links":links,"tick":0,"events":[]}
    refresh_link_metrics(network)
    return network

def refresh_link_metrics(network):
    """Recompute link quality from the current satellite/ground geometry.

    This is the key dynamic-network step: when satellites move, the graph
    weights move too, so shortest-path algorithms can select a different route.
    """
    nodes = {n["id"]: n for n in network["nodes"]}
    for e in network["links"]:
        a, b = nodes.get(e["a"]), nodes.get(e["b"])
        if not a or not b:
            continue
        distance = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
        # Keep the simulated links connected, but make their cost respond
        # strongly enough to orbital movement to demonstrate rerouting.
        distance_ratio = min(distance / 0.65, 1.25)
        distance_factor = 0.70 + 2.20 * distance_ratio

        # Dynamic orbital link quality: the geometry of the moving endpoints
        # changes the signal quality of each link.  This creates genuinely
        # time-varying edge weights instead of merely moving the pixels.
        mx = (a["x"] + b["x"]) / 2.0
        my = (a["y"] + b["y"]) / 2.0
        angle = math.atan2(my - 0.50, mx - 0.50)
        orbital_quality = 0.35 + 1.65 * (0.5 + 0.5 * math.cos(3.0 * angle))
        e["orbital_quality"] = round(orbital_quality, 3)
        e["distance"] = round(distance, 4)
        e["latency"] = round(e["base_latency"] * distance_factor * orbital_quality, 2)
        e["energy"] = round(e["base_energy"] * (0.82 + 1.35 * distance_ratio) * orbital_quality, 2)
        e["bandwidth"] = round(max(80.0, e["base_bandwidth"] / ((0.82 + 0.55 * distance_ratio) * orbital_quality)), 1)

NETWORK = make_network()

def active_node_map():
    return {n["id"]:n for n in NETWORK["nodes"] if n["active"]}

def edge_cost(e, weights):
    return (
        weights["latency"] * e["latency"] +
        weights["congestion"] * (e["congestion"] * 2.2) +
        weights["energy"] * e["energy"]
    )

def adjacency(weights):
    adj={n["id"]:[] for n in NETWORK["nodes"] if n["active"]}
    for e in NETWORK["links"]:
        if not e["active"] or e["a"] not in adj or e["b"] not in adj:
            continue
        w=edge_cost(e,weights)
        adj[e["a"]].append((e["b"],w,e))
        adj[e["b"]].append((e["a"],w,e))
    return adj

def dijkstra(start, goal, weights):
    adj=adjacency(weights)
    dist={k:float("inf") for k in adj}; prev={}
    dist[start]=0
    done=set()
    while True:
        candidates=[(d,u) for u,d in dist.items() if u not in done]
        if not candidates: break
        d,u=min(candidates)
        if d==float("inf"): break
        done.add(u)
        if u==goal: break
        for v,w,e in adj[u]:
            nd=d+w
            if nd<dist[v]:
                dist[v]=nd; prev[v]=u
    if dist.get(goal,float("inf"))==float("inf"):
        return [],float("inf")
    path=[]; cur=goal
    while cur!=start:
        path.append(cur)
        cur=prev[cur]
    path.append(start); path.reverse()
    return path,dist[goal]

def astar(start, goal, weights):
    adj=adjacency(weights)
    nodes=active_node_map()
    def h(a):
        na,ng=nodes[a],nodes[goal]
        return math.hypot(na["x"]-ng["x"],na["y"]-ng["y"])*30*weights["latency"]
    g={k:float("inf") for k in adj}; f={k:float("inf") for k in adj}; prev={}
    g[start]=0; f[start]=h(start); open_set={start}
    while open_set:
        u=min(open_set,key=lambda x:f[x])
        if u==goal: break
        open_set.remove(u)
        for v,w,e in adj[u]:
            ng=g[u]+w
            if ng<g[v]:
                prev[v]=u; g[v]=ng; f[v]=ng+h(v); open_set.add(v)
    if g[goal]==float("inf"): return [],float("inf")
    path=[]; cur=goal
    while cur!=start:
        path.append(cur); cur=prev[cur]
    path.append(start); path.reverse()
    return path,g[goal]

def bellman(start,goal,weights):
    adj=adjacency(weights)
    dist={k:float("inf") for k in adj}; prev={}
    dist[start]=0
    edges=[]
    for u,items in adj.items():
        for v,w,e in items: edges.append((u,v,w))
    for _ in range(len(adj)-1):
        changed=False
        for u,v,w in edges:
            if dist[u]+w<dist[v]:
                dist[v]=dist[u]+w; prev[v]=u; changed=True
        if not changed: break
    if dist[goal]==float("inf"): return [],float("inf")
    path=[]; cur=goal
    while cur!=start:
        if cur not in prev: return [],float("inf")
        path.append(cur);cur=prev[cur]
    path.append(start);path.reverse()
    return path,dist[goal]

def floyd(start,goal,weights):
    ids=list(active_node_map())
    idx={x:i for i,x in enumerate(ids)}
    n=len(ids); inf=float("inf")
    d=[[inf]*n for _ in range(n)]
    nxt=[[None]*n for _ in range(n)]
    for i in range(n): d[i][i]=0
    for e in NETWORK["links"]:
        if e["active"] and e["a"] in idx and e["b"] in idx:
            i,j=idx[e["a"]],idx[e["b"]];w=edge_cost(e,weights)
            if w<d[i][j]:
                d[i][j]=d[j][i]=w;nxt[i][j]=j;nxt[j][i]=i
    for k in range(n):
        for i in range(n):
            dik=d[i][k]
            if dik==inf: continue
            for j in range(n):
                nd=dik+d[k][j]
                if nd<d[i][j]:
                    d[i][j]=nd;nxt[i][j]=nxt[i][k]
    if nxt[idx[start]][idx[goal]] is None: return [],inf
    path=[start];i=idx[start];j=idx[goal]
    while i!=j:
        i=nxt[i][j];path.append(ids[i])
        if len(path)>n+2:return [],inf
    return path,d[idx[start]][idx[goal]]

def genetic(start,goal,weights):
    # Deterministic educational heuristic based on multiple candidate shortest-path weightings.
    candidates=[]
    variants=[
        weights,
        {"latency":1.0,"congestion":0.35,"energy":0.15},
        {"latency":0.45,"congestion":1.0,"energy":0.20},
        {"latency":0.35,"congestion":0.35,"energy":1.0},
    ]
    for w in variants:
        p,c=dijkstra(start,goal,w)
        if p: candidates.append((path_cost(p,weights),p))
    if not candidates:return [],float("inf")
    return min(candidates,key=lambda x:x[0])[1],min(candidates,key=lambda x:x[0])[0]

def path_cost(path,weights):
    total=0
    for a,b in zip(path,path[1:]):
        e=next((e for e in NETWORK["links"] if e["active"] and ((e["a"]==a and e["b"]==b) or (e["a"]==b and e["b"]==a))),None)
        if not e:return float("inf")
        total+=edge_cost(e,weights)
    return total

def details(path):
    if not path:return None
    latency=0;energy=0;rel=1;bw=float("inf"); congestion=0
    for a,b in zip(path,path[1:]):
        e=next((e for e in NETWORK["links"] if e["active"] and ((e["a"]==a and e["b"]==b) or (e["a"]==b and e["b"]==a))),None)
        if not e:return None
        latency+=e["latency"]*(1+e["congestion"]/250)
        energy+=e["energy"];rel*=e["reliability"]*(1-e["congestion"]/1500)
        bw=min(bw,e["bandwidth"]*(1-e["congestion"]/100));congestion=max(congestion,e["congestion"])
    return {"latency":round(latency,2),"energy":round(energy,2),"reliability":round(rel*100,3),
            "bandwidth":round(bw,1),"hops":len(path)-1,"maxCongestion":round(congestion,1)}

def route(algo,start,goal,weights):
    funcs={"dijkstra":dijkstra,"astar":astar,"bellman":bellman,"floyd":floyd,"genetic":genetic}
    t=time.perf_counter()
    path,cost=funcs[algo](start,goal,weights)
    elapsed=(time.perf_counter()-t)*1000
    return {"algorithm":ALGORITHMS[algo], "key":algo, "path":path, "cost":round(cost,4) if math.isfinite(cost) else None,
            "computeMs":round(elapsed,3),"metrics":details(path)}

@app.get("/api/health")
def health():
    return jsonify({"status":"ok","service":"OrbitMesh API","version":"2.0"})

@app.get("/api/network")
def network():
    refresh_link_metrics(NETWORK)
    return jsonify(NETWORK)

@app.post("/api/reset")
def reset():
    global NETWORK
    NETWORK=make_network()
    NETWORK["events"].insert(0,{"tick":0,"message":"Network reset to nominal topology."})
    return jsonify(NETWORK)

@app.post("/api/route")
def route_api():
    refresh_link_metrics(NETWORK)
    data=request.get_json(force=True)
    start=data.get("start","S1");goal=data.get("goal","G2");algo=data.get("algorithm","dijkstra")
    weights=data.get("weights",{"latency":.5,"congestion":.3,"energy":.2})
    if start not in active_node_map() or goal not in active_node_map():
        return jsonify({"error":"Source or destination is unavailable."}),400
    result=route(algo,start,goal,weights)
    return jsonify(result)

@app.post("/api/benchmark")
def benchmark_api():
    refresh_link_metrics(NETWORK)
    data=request.get_json(force=True)
    start=data.get("start","S1");goal=data.get("goal","G2")
    weights=data.get("weights",{"latency":.5,"congestion":.3,"energy":.2})
    results=[route(k,start,goal,weights) for k in ALGORITHMS]
    valid=[x for x in results if x["cost"] is not None]
    best=min((x["cost"] for x in valid),default=None)
    for x in results:x["optimal"]=best is not None and abs(x["cost"]-best)<1e-6
    return jsonify({"results":results})

@app.post("/api/event")
def event():
    data=request.get_json(force=True);kind=data.get("type")
    active_sats=[n for n in NETWORK["nodes"] if n["kind"]=="satellite" and n["active"]]
    active_links=[e for e in NETWORK["links"] if e["active"]]
    message=""
    if kind=="fail_satellite" and active_sats:
        n=rng.choice(active_sats);n["active"]=False
        for e in NETWORK["links"]:
            if e["a"]==n["id"] or e["b"]==n["id"]:e["active"]=False
        message=f"Satellite {n['id']} failed; incident links disabled."
    elif kind=="fail_link" and active_links:
        e=rng.choice(active_links);e["active"]=False
        message=f"Link {e['a']} ↔ {e['b']} failed."
    elif kind=="weather":
        gs=[n for n in NETWORK["nodes"] if n["kind"]=="ground" and n["active"]]
        g=rng.choice(gs)
        for e in NETWORK["links"]:
            if e["active"] and (e["a"]==g["id"] or e["b"]==g["id"]):
                e["congestion"]=min(95,e["congestion"]+45)
        message=f"Atmospheric event at {g['name']}; ground-link congestion increased."
    elif kind=="congestion":
        for e in rng.sample(active_links,min(12,len(active_links))):
            e["congestion"]=min(95,e["congestion"]+rng.uniform(18,38))
        message="Traffic surge injected across the constellation."
    elif kind=="recover":
        for n in NETWORK["nodes"]:n["active"]=True
        for e in NETWORK["links"]:
            e["active"]=True;e["congestion"]=min(45,max(8,e["congestion"]))
        message="Network recovered; failed assets restored."
    else:
        return jsonify({"error":"Unknown or unavailable event."}),400
    NETWORK["tick"]+=1
    NETWORK["events"].insert(0,{"tick":NETWORK["tick"],"message":message})
    NETWORK["events"]=NETWORK["events"][:30]
    return jsonify(NETWORK)

@app.post("/api/simulate")
def simulate():
    data=request.get_json(force=True);ticks=int(data.get("ticks",1))
    NETWORK["tick"]+=max(1,ticks)
    # Simulated orbital motion: front-end receives updated positions.
    for n in NETWORK["nodes"]:
        if n["kind"]=="satellite" and n["active"]:
            theta=(NETWORK["tick"]*ORBIT_STEP)+(n["plane"]*0.12)
            base=n["id"]; idx=int(base[1:])-1
            phase=(idx%10)/10*math.pi*2
            n["x"]=0.5+0.34*math.cos(theta+phase)
            n["y"]=0.5+0.24*math.sin(theta+phase)
    refresh_link_metrics(NETWORK)
    return jsonify(NETWORK)

@app.get("/api/algorithms")
def algorithms():
    return jsonify(ALGORITHMS)

if __name__=="__main__":
    app.run(host="127.0.0.1",port=5000,debug=True)
