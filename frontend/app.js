const API="http://127.0.0.1:5000/api";
const $=id=>document.getElementById(id);
let network=null, running=true, tickTimer=null;
let weights={latency:.50,congestion:.30,energy:.20};
let lastResult=null;
let lastPathKey="";

async function api(path,opts={}){
  const r=await fetch(API+path,{headers:{"Content-Type":"application/json"},...opts});
  if(!r.ok) throw new Error((await r.json()).error||`HTTP ${r.status}`);
  return r.json();
}
function payload(){return {start:$("source").value,goal:$("destination").value,algorithm:$("algorithm").value,weights};}
function setApi(ok){$("apiDot").classList.toggle("ok",ok);$("apiText").textContent=ok?"API ONLINE":"API OFFLINE";}
async function boot(){
  try{network=await api("/network");setApi(true);populate();render();await calculate();}
  catch(e){setApi(false);toast("Backend unavailable. Start the Flask server first.");console.error(e)}
}
function populate(){
  const sats=network.nodes.filter(n=>n.kind==="satellite"&&n.active),gs=network.nodes.filter(n=>n.kind==="ground");
  $("source").innerHTML=sats.map(n=>`<option value="${n.id}">${n.id}</option>`).join("");
  $("destination").innerHTML=gs.map(n=>`<option value="${n.id}">${n.id} · ${n.name}</option>`).join("");
  $("source").value="S1";$("destination").value="G2";
}
async function calculate(){
  try{
    const r=await api("/route",{method:"POST",body:JSON.stringify(payload())});
    lastResult=r;
    const pathKey=r.path.join("→");
    if(pathKey!==lastPathKey){ if(lastPathKey) toast(`ROUTE CHANGED · T+${String(network.tick).padStart(4,"0")}`); lastPathKey=pathKey; }
    renderResult(r);render();updateExplanation();
  }catch(e){toast(e.message)}
}
function renderResult(r){
  const m=r.metrics;
  $("routePath").textContent=r.path.length?r.path.join("  →  "):"NO AVAILABLE ROUTE";
  $("algoBadge").textContent=r.algorithm.name;
  $("latencyM").textContent=m?m.latency.toFixed(1)+" ms":"—";
  $("bandwidthM").textContent=m?m.bandwidth.toFixed(0)+" Mbps":"—";
  $("reliabilityM").textContent=m?m.reliability.toFixed(2)+"%":"—";
  $("energyM").textContent=m?m.energy.toFixed(1):"—";
  $("hopsM").textContent=m?m.hops:"—";
  $("cost").textContent=r.cost??"—";
  $("compute").textContent=r.computeMs+" ms";
  $("nodes").textContent=network.nodes.filter(n=>n.active).length;
  $("links").textContent=network.links.filter(e=>e.active).length;
  $("algoBadge").title=r.algorithm.complexity;
}
function updateExplanation(){
  const r=lastResult?.algorithm;
  if(!r)return;
  $("explain").innerHTML=`<h3>${r.name} · ${r.type}</h3><p>${r.explanation}</p><p style="margin-top:5px;color:#88a6b5">Complexity: <b>${r.complexity}</b></p>`;
}
async function benchmark(){
  try{
    $("benchBody").innerHTML=`<tr><td colspan="5">Running benchmark…</td></tr>`;
    const r=await api("/benchmark",{method:"POST",body:JSON.stringify(payload())});
    $("benchBody").innerHTML=r.results.map(x=>`<tr><td>${x.algorithm.name}</td><td>${x.cost??"—"}</td><td>${x.computeMs} ms</td><td>${x.metrics?.hops??"—"}</td><td class="${x.optimal?"optimal":"alternate"}">${x.optimal?"OPTIMAL":"ALTERNATE"}</td></tr>`).join("");
  }catch(e){toast(e.message)}
}
async function event(type){
  try{
    network=await api("/event",{method:"POST",body:JSON.stringify({type})});
    const msg=network.events[0]?.message||type;
    $("currentEvent").innerHTML=`<i class="incident-dot"></i><span>${msg}</span>`;
    toast(msg);render();await calculate();
  }catch(e){toast(e.message)}
}
async function reset(){
  network=await api("/reset",{method:"POST",body:"{}"});
  $("currentEvent").innerHTML=`<i class="incident-dot"></i><span>Scenario reset to nominal topology.</span>`;
  populate();render();await calculate();
}
async function simulate(){
  if(!running){$("simState").textContent="SIMULATION PAUSED";return;}
  $("simState").textContent="LIVE SIMULATION";
  try{
    network=await api("/simulate",{method:"POST",body:JSON.stringify({ticks:1})});
    // Orbital motion changes link geometry, so recalculate the route on every tick.
    const r=await api("/route",{method:"POST",body:JSON.stringify(payload())});
    lastResult=r;
    const pathKey=r.path.join("→");
    if(pathKey && pathKey!==lastPathKey){
      if(lastPathKey) toast(`ROUTE CHANGED at T+${String(network.tick).padStart(4,"0")}`);
      lastPathKey=pathKey;
    }
    renderResult(r);
    render();
  }catch(e){running=false;toast("Backend connection lost.");}
}
function render(){
  if(!network)return;
  const activeNodes=network.nodes.filter(n=>n.active).length;
  const activeLinks=network.links.filter(e=>e.active).length;
  const health=Math.round(activeNodes/network.nodes.length*100);
  $("health").textContent=health+"%";
  document.querySelector(".health-ring").style.background=`conic-gradient(var(--cyan) 0 ${health}%, #10202a ${health}% 100%)`;
  $("satCount").textContent=network.nodes.filter(n=>n.kind==="satellite"&&n.active).length+"/"+network.nodes.filter(n=>n.kind==="satellite").length;
  $("groundCount").textContent=network.nodes.filter(n=>n.kind==="ground"&&n.active).length+"/"+network.nodes.filter(n=>n.kind==="ground").length;
  $("linkCount").textContent=activeLinks;
  $("simTick").textContent=String(network.tick).padStart(4,"0");
  renderLog();renderTelemetry();draw();
}
function renderLog(){
  $("log").innerHTML=(network.events||[]).slice(0,12).map(e=>`<div class="logrow"><time>T+${String(e.tick).padStart(4,"0")}</time><span>${e.message}</span></div>`).join("");
}
function renderTelemetry(){
  const arr=network.links.filter(e=>e.active).sort((a,b)=>b.congestion-a.congestion).slice(0,8);
  $("telemetry").innerHTML=arr.map(e=>`<div class="tele-row"><span>${e.a}↔${e.b}</span><div class="bar"><i style="width:${e.congestion}%"></i></div><b>${e.congestion.toFixed(0)}%</b></div>`).join("");
}
function draw(){
  const c=$("canvas"),ctx=c.getContext("2d"),dpr=devicePixelRatio||1,r=c.getBoundingClientRect();
  c.width=r.width*dpr;c.height=r.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
  const w=r.width,h=r.height;
  ctx.clearRect(0,0,w,h);
  // starfield
  for(let i=0;i<100;i++){ctx.fillStyle=`rgba(170,215,235,${.08+(i%5)*.025})`;ctx.fillRect((i*71)%w,(i*37)%h,1,1)}
  const byId=id=>network.nodes.find(n=>n.id===id);
  // earth
  const cx=w*.5,cy=h*.55,rad=Math.min(w,h)*.18;
  const g=ctx.createRadialGradient(cx-rad*.35,cy-rad*.4,2,cx,cy,rad);
  g.addColorStop(0,"#173c50");g.addColorStop(1,"#06141d");
  ctx.beginPath();ctx.arc(cx,cy,rad,0,Math.PI*2);ctx.fillStyle=g;ctx.fill();
  ctx.strokeStyle="rgba(98,169,255,.22)";ctx.stroke();
  // links
  for(const e of network.links){
    const a=byId(e.a),b=byId(e.b);if(!a||!b||!a.active||!b.active||!e.active)continue;
    const route=lastResult?.path||[];
    const selected=route.includes(a.id)&&route.includes(b.id)&&Math.abs(route.indexOf(a.id)-route.indexOf(b.id))===1;
    ctx.beginPath();ctx.moveTo(a.x*w,a.y*h);ctx.lineTo(b.x*w,b.y*h);
    ctx.strokeStyle=selected?"#66a9ff":"rgba(56,102,123,.27)";ctx.lineWidth=selected?2.5:.7;ctx.stroke();
  }
  // nodes
  for(const n of network.nodes){
    const x=n.x*w,y=n.y*h;
    ctx.globalAlpha=n.active?1:.16;
    ctx.beginPath();ctx.arc(x,y,n.kind==="ground"?5:3.3,0,Math.PI*2);
    ctx.fillStyle=n.kind==="ground"?"#66a9ff":"#62d9c0";ctx.shadowBlur=9;ctx.shadowColor=ctx.fillStyle;ctx.fill();ctx.shadowBlur=0;
    if(n.kind==="ground"||lastResult?.path?.includes(n.id)){ctx.font="8px Inter";ctx.fillStyle="#9eb6c1";ctx.fillText(n.id,x+7,y-7)}
    ctx.globalAlpha=1;
  }
}
function toast(msg){const el=$("toast");el.textContent=msg;el.classList.add("show");clearTimeout(window.__toast);window.__toast=setTimeout(()=>el.classList.remove("show"),2500)}
function bind(){
  $("route").onclick=calculate;$("benchmark").onclick=benchmark;$("reset").onclick=reset;$("recover").onclick=()=>event("recover");
  document.querySelectorAll("[data-event]").forEach(b=>b.onclick=()=>event(b.dataset.event));
  $("clearLog").onclick=()=>{network.events=[];renderLog()};
  $("pause").onclick=()=>{running=!running;$("pause").textContent=running?"Ⅱ  PAUSE":"▶  RESUME";$("simState").textContent=running?"LIVE SIMULATION":"SIMULATION PAUSED"};
  $("step").onclick=async()=>{
    running=false;$("pause").textContent="RESUME";
    network=await api("/simulate",{method:"POST",body:JSON.stringify({ticks:1})});
    const r=await api("/route",{method:"POST",body:JSON.stringify(payload())});
    lastResult=r;
    const pathKey=r.path.join("→");
    if(pathKey!==lastPathKey){ if(lastPathKey) toast(`ROUTE CHANGED · T+${String(network.tick).padStart(4,"0")}`); lastPathKey=pathKey; }
    renderResult(r);render();
  };
  ["latency","congestion","energy"].forEach(id=>{
    $(id).oninput=()=>{weights[id]=Number($(id).value)/100;$(id+"V").textContent=$(id).value+"%";$("weightTotal").textContent=Math.round((weights.latency+weights.congestion+weights.energy)*100)+"%"};
  });
  $("normalize").onclick=()=>{let s=weights.latency+weights.congestion+weights.energy;for(const id of ["latency","congestion","energy"]){weights[id]/=s;$(id).value=Math.round(weights[id]*100);$(id+"V").textContent=$(id).value+"%"}$("weightTotal").textContent="100%"};
  $("source").onchange=calculate;$("destination").onchange=calculate;$("algorithm").onchange=()=>{calculate();updateExplanation()};
  setInterval(()=>{const d=new Date();$("clock").textContent=d.toLocaleTimeString("en-GB",{hour12:false})},1000);
  setInterval(simulate,900);
  window.addEventListener("resize",draw);
}
bind();boot();
