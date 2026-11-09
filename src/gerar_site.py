"""
conatusride — gerador do painel.

Lê o banco e escreve o painel em docs/site/: por ora a tela inicial, o detalhe
do mês, o histórico, a comparação entre anos, os recordes e o mapa.

O mapa só é gerado se data/contornos.json existir — rode src/contornos.py uma
vez para criá-lo.

Os dados vão embutidos no HTML, não em arquivo separado: navegador aberto em
file:// bloqueia leitura de JSON local, e assim cada página funciona sozinha,
inclusive copiada para o celular.

O detalhe do mês é uma página só que recebe o mês pela URL (?a=2026&m=8) — um
arquivo por mês seriam uns 60 para o mesmo resultado.

Ordem: importar.py -> pontos_partida.py -> tracos.py -> metas.py ->
       classificar.py -> gerar_site.py

Uso:
    python src/gerar_site.py
"""

from pathlib import Path
import json

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "conatusride.duckdb"
SAIDA = RAIZ / "docs" / "site"

# Ordem do menu. As que ainda não existem aparecem apagadas.
SECOES = [
    ("index.html", "início"),
    ("mes.html", "mês"),
    ("historico.html", "histórico"),
    ("recordes.html", "recordes"),
    ("anos.html", "anos"),
    ("mapa.html", "mapa"),
]

# Minutos dentro de um município para a cidade contar na rota. Mesmo corte do
# classificar.py: passagem de raspão não é ter estado lá.
MIN_PERMANENCIA = 5

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#faf9f7;color:#1a1a19;line-height:1.55;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
-webkit-font-smoothing:antialiased}
.wrap{max-width:1000px;margin:0 auto;padding:1.5rem 1.25rem 4rem}
nav{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:1.75rem;
border-bottom:1px solid #e4e2db;padding-bottom:.75rem}
nav a{font-size:13px;padding:6px 14px;border-radius:20px;text-decoration:none;color:#6b6a65}
nav a:hover{background:#efeee9;color:#1a1a19}
nav a.on{background:#1a1a19;color:#faf9f7}
nav a.off{opacity:.35;pointer-events:none}

.filtros{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:1.25rem}
.sel{position:relative;display:inline-block}
.sel select{appearance:none;-webkit-appearance:none;background:#fff;border:1px solid #e4e2db;
border-radius:8px;padding:.45rem 2rem .45rem .8rem;font:inherit;font-size:13px;color:#1a1a19;cursor:pointer}
.sel select:hover{border-color:#b8b5ad}
.sel select:focus{outline:none;border-color:#1a1a19}
.sel::after{content:"";position:absolute;right:.7rem;top:50%;width:6px;height:6px;pointer-events:none;
border-right:1.5px solid #8a8880;border-bottom:1.5px solid #8a8880;transform:translateY(-70%) rotate(45deg)}
.sel.on select{border-color:#1a1a19;background:#f4f3ef}
.ctx{font-size:13px;color:#8a8880;margin-left:auto}
.busca{background:#fff;border:1px solid #e4e2db;border-radius:8px;padding:.45rem .8rem;
font:inherit;font-size:13px;color:#1a1a19;width:170px}
.busca:focus{outline:none;border-color:#1a1a19}
.faixa-km{display:flex;gap:10px;align-items:center;font-size:13px;color:#6b6a65;margin-bottom:1.1rem}
.faixa-km input[type=range]{flex:1;max-width:200px;accent-color:#1baf7a}
.limpar{background:#fff;border:1px solid #e4e2db;border-radius:8px;padding:.4rem .9rem;
font:inherit;font-size:13px;color:#6b6a65;cursor:pointer;margin-left:auto}
.limpar:hover{border-color:#b8b5ad;color:#1a1a19}

.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:10px}
.card{background:#fff;border:1px solid #eeece6;border-radius:10px;padding:1rem;text-align:center}
.card .ic{font-size:20px;line-height:1;margin-bottom:.4rem;opacity:.8}
.card .lb{font-size:12px;color:#6b6a65;margin-bottom:.1rem}
.card .vl{font-size:27px;font-weight:600;color:#eb6834;line-height:1.1}
.card .un{font-size:12px;color:#8a8880;font-weight:400}
.minis{display:grid;grid-template-columns:repeat(auto-fit,minmax(112px,1fr));gap:8px}
.mini{background:#f4f3ef;border-radius:8px;padding:.6rem .8rem}
.mini .lb{font-size:11px;color:#6b6a65}
.mini .vl{font-size:17px;font-weight:500}

h2{font-size:15px;font-weight:500;margin:2rem 0 .8rem}
h2 small{font-weight:400;color:#8a8880;font-size:12px;margin-left:6px}
.tit{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:1.1rem}
.tit b{font-size:28px;font-weight:600}
.tit span{font-size:14px;color:#8a8880}

.wk{display:flex;align-items:center;gap:10px;margin-bottom:5px;cursor:pointer}
.wk .rot{width:82px;flex:none;font-size:12px;color:#6b6a65}
.wk .trk{flex:1;height:22px;border-radius:5px;background:#efeee9;overflow:hidden}
.wk .trk i{display:block;height:100%;border-radius:5px}
.wk .val{width:126px;flex:none;text-align:right;font-size:12px;color:#6b6a65}
.wk:hover .trk i{opacity:.75}

.meses{display:flex;align-items:flex-end;gap:6px;height:155px}
.col{flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:100%;cursor:pointer}
.col .bar{border-radius:5px 5px 0 0;min-height:4px}
.col:hover .bar{opacity:.75}
.col .v,.col .l,.col .p{text-align:center;font-size:11px;color:#8a8880}
.col .v{margin-bottom:3px}
.col .l{margin-top:5px}
.col .p{font-size:10px}
.col.on .l{color:#1a1a19}

.dim{margin-bottom:.9rem}
.dim .t{font-size:12px;color:#8a8880;margin-bottom:4px}
.faixa{display:flex;height:30px;border-radius:5px;overflow:hidden;gap:2px}
.faixa div{display:flex;flex-direction:column;justify-content:center;padding:0 9px;
color:#123;font-size:11px;line-height:1.15;overflow:hidden}
.faixa span{white-space:nowrap}
.faixa .q{font-weight:600}

.tabela{background:#fff;border:1px solid #eeece6;border-radius:10px;overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 10px;font-weight:500;color:#6b6a65;
border-bottom:1px solid #e4e2db;white-space:nowrap}
td{padding:8px 10px;border-bottom:0.5px solid #eeece6}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:#faf9f7}
.novo{font-size:11px;padding:1px 8px;border-radius:20px;background:#1baf7a33;margin-left:6px}
.dt{font-size:12px;color:#6b6a65;background:#f4f3ef;border-radius:4px;
padding:1px 7px;margin:0 4px 3px 0;white-space:nowrap;display:inline-block}

/* Histórico: cabeçalho fixo, linha que abre a rota ao clique. */
.rolagem{max-height:560px;overflow:auto}
.rolagem th{position:sticky;top:0;background:#fff;z-index:1;cursor:pointer}
.rolagem th.fixo{cursor:default}
.rolagem th.dir,.rolagem td.dir{text-align:right;white-space:nowrap}
tr.abre{cursor:pointer}
tr.abre.aberta td{background:#f7f6f2}
.ar{display:inline-block;width:11px;color:#b8b5ad}
tr.rota td{padding:0 10px 10px 30px;font-size:12px;color:#6b6a65;background:#f7f6f2}
.total{font-size:12px;color:#8a8880;margin:.6rem 0 0}

/* Anos: tabela comparativa e meses lado a lado. */
.chk{display:flex;align-items:center;gap:7px;font-size:13px;color:#6b6a65;cursor:pointer}
.chk input{accent-color:#1baf7a;cursor:pointer}
.pt{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:7px}
.melhor{font-size:11px;padding:1px 7px;border-radius:20px;background:#1baf7a33;margin-left:6px}
.up{color:#1baf7a}.down{color:#eb6834}
.un{color:#8a8880;font-weight:400;font-size:11px}
.gmes{display:flex;gap:8px;align-items:flex-end;height:190px}
.gmes .m{flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:100%}
.gmes .pilha{display:flex;gap:1px;align-items:flex-end;height:100%}
.gmes .pilha i{flex:1;border-radius:2px 2px 0 0;display:block}
.gmes .rot{text-align:center;font-size:11px;color:#8a8880;margin-top:5px}
.leg{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px;font-size:12px;color:#8a8880}
.leg span{display:flex;align-items:center;gap:5px}

/* Recordes: cartões para o recorde de um pedal, tabela para os de período. */
.rec{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:10px;margin-bottom:2rem}
.rec .c{background:#fff;border:1px solid #eeece6;border-radius:10px;padding:1rem}
.rec .ic{font-size:19px;line-height:1;margin-bottom:.45rem;opacity:.85}
.rec .lb{font-size:12px;color:#6b6a65}
.rec .vl{font-size:26px;font-weight:600;color:#eb6834;line-height:1.15}
.rec .qual{font-size:13px;margin-top:.35rem}
.rec .quando{font-size:12px;color:#8a8880}
h3{font-size:15px;font-weight:500;margin:0 0 .9rem}

/* Mapa: SVG desenhado a partir dos contornos do IBGE, sem camada externa. */
.mapa{background:#fff;border:1px solid #eeece6;border-radius:10px;overflow:hidden}
.mapa svg{display:block;width:100%;height:auto}
.mapa path{stroke:#fff;stroke-width:.4;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.mapa .vazio{fill:#eeece6}
.mapa .tem{fill:#9fd6c0;cursor:pointer}
.mapa .tem:hover{fill:#5DCAA5}
.mapa .sel{fill:#eb6834}
.topo{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:1rem;font-size:13px}
.topo a{color:#6b6a65;text-decoration:none;cursor:pointer}
.topo a:hover{color:#1a1a19;text-decoration:underline}
.topo b{font-weight:500}
.topo .sep{color:#c9c6bd}
.painel{display:grid;grid-template-columns:1fr 290px;gap:16px;align-items:start}
.lado{background:#f4f3ef;border-radius:10px;padding:1rem}
.lado h4{font-size:14px;font-weight:500;margin:0 0 .5rem}
.lado .l{display:flex;justify-content:space-between;gap:10px;font-size:13px;
padding:5px 0;border-bottom:0.5px solid #e4e2db;cursor:pointer}
.lado .l:last-child{border-bottom:none}
.lado .l:hover{color:#eb6834}
.lado .l.on{color:#eb6834;font-weight:500}
.lado .l span{color:#8a8880}
.lado .rol{max-height:330px;overflow:auto}
.lado p{font-size:13px;color:#6b6a65;margin:.25rem 0}
@media(max-width:760px){.painel{grid-template-columns:1fr}}

.ped{border-top:0.5px solid #eeece6;padding:.85rem 0}
.ped .linha{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.ped .dia{font-size:12px;color:#8a8880;width:46px;flex:none}
.ped .nome{flex:1;min-width:150px;font-size:14px}
.ped .km{font-size:18px;font-weight:600}
.ped .num{font-size:13px;color:#6b6a65;text-align:right}
.ped .rota{font-size:12px;color:#8a8880;margin-top:5px;line-height:1.6}
.tag{font-size:11px;padding:2px 9px;border-radius:20px;margin-left:5px;white-space:nowrap}
.vazio{padding:2rem;text-align:center;color:#8a8880;font-size:13px}

footer{margin-top:3.5rem;padding-top:1rem;border-top:1px solid #e4e2db;font-size:12px;color:#8a8880}
@media(max-width:640px){.card .vl{font-size:22px}.wk .val{width:92px}.wk .rot{width:66px}
.busca{width:100%}}
"""

COMUM = """
const MS=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
const ML=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
          "setembro","outubro","novembro","dezembro"];
const CORES={
  piso:{estrada:"#B5D4F4",misto:"#eda100",trilha:"#eb6834"},
  porte:{curto:"#B5D4F4",medio:"#378ADD",longo:"#185FA5"},
  tipo:{rotina:"#B5D4F4",exploracao:"#1baf7a"}
};
const br=n=>Math.round(n).toLocaleString("pt-BR");
const hm=m=>Math.floor(m/60)+"h"+String(Math.round(m%60)).padStart(2,"0");
const dia=s=>{const p=s.split("-");return (+p[2])+" "+MS[+p[1]-1];};
const $=id=>document.getElementById(id);
const anos=()=>[...new Set(D.map(r=>r.a))].sort((x,y)=>y-x);
function opts(el,lista,rot,vazio){
  el.innerHTML=(vazio===undefined?"":'<option value="">'+vazio+'</option>')+
    lista.map(v=>'<option value="'+v+'">'+rot(v)+'</option>').join("");
}
function composicao(L){
  const n=L.length;
  return [["piso","s"],["porte","p"],["tipo","c"]].map(([nome,k])=>{
    const cores=CORES[nome],q={};
    L.forEach(r=>q[r[k]]=(q[r[k]]||0)+1);
    const kk=Object.keys(cores).filter(x=>q[x]);
    if(!kk.length)return"";
    return '<div class="dim"><div class="t">'+nome+'</div><div class="faixa">'+
      kk.map(x=>'<div title="'+x+': '+q[x]+'" style="width:'+(100*q[x]/n)+
        '%;background:'+cores[x]+'"><span>'+x+'</span><span class="q">'+q[x]+
        '</span></div>').join("")+'</div></div>';
  }).join("");
}
function etiquetas(r){
  let h="";
  if(r.c==="exploracao")h+='<span class="tag" style="background:'+CORES.tipo.exploracao+'44">exploração</span>';
  if(r.s!=="estrada")h+='<span class="tag" style="background:'+CORES.piso[r.s]+'44">'+r.s+'</span>';
  return h;
}
"""

SCRIPT_INICIO = """
const fa=$("fa"),fm=$("fm"),fw=$("fw");
const meses=()=>[...new Set(D.filter(r=>r.a==+fa.value).map(r=>r.m))].sort((x,y)=>x-y);
const semanasDe=()=>[...new Set(D.filter(r=>r.a==+fa.value&&
  (!fm.value||r.m==+fm.value)).map(r=>r.w))].sort((x,y)=>x-y);

opts(fa,anos(),v=>v);
fa.value=anos()[0];
const ANO_ATUAL=anos()[0];
opts(fm,meses(),v=>ML[v-1],"ano inteiro");
// O ano corrente abre no mês mais recente com pedal — a tela é sobre o agora.
// Ano fechado abre inteiro: dezembro não tem nada de especial em retrospecto.
if(+fa.value===ANO_ATUAL)fm.value=String(Math.max(...meses()));
opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");

function render(){
  [fm,fw].forEach(e=>e.parentElement.classList.toggle("on",!!e.value));
  const A=+fa.value;
  const L=D.filter(r=>r.a===A&&(!fm.value||r.m==+fm.value)&&(!fw.value||r.w==+fw.value));
  $("ctx").textContent=fw.value?"semana "+fw.value+" · "+A
    :fm.value?ML[+fm.value-1]+" de "+A:A+" · ano inteiro";

  const n=L.length,km=L.reduce((s,r)=>s+r.km,0),mi=L.reduce((s,r)=>s+r.t,0),
        el=L.reduce((s,r)=>s+r.e,0);
  const dias=[...new Set(L.map(r=>r.d))].sort();
  let seq=dias.length?1:0,mx=seq;
  for(let i=1;i<dias.length;i++){
    seq=(new Date(dias[i])-new Date(dias[i-1]))/864e5===1?seq+1:1;
    mx=Math.max(mx,seq);
  }

  $("cards").innerHTML=[
    ["🚴","Total Km",br(km),"km"],
    ["⏱","Vel. Média",n?(L.reduce((s,r)=>s+r.v,0)/n).toFixed(1):"0","km/h"],
    ["🚲","Pedais",n,""],
    ["🕐","Horas",hm(mi),""],
    ["⛰","Elevação",br(el),"m"]
  ].map(c=>'<div class="card"><div class="ic">'+c[0]+'</div><div class="lb">'+c[1]+
    '</div><div class="vl">'+c[2]+' <span class="un">'+c[3]+'</span></div></div>').join("");

  $("minis").innerHTML=[
    ["maior pedal",n?Math.max(...L.map(r=>r.km)).toFixed(1)+" km":"—"],
    ["maior subida",n?br(Math.max(...L.map(r=>r.e)))+" m":"—"],
    ["média por pedal",n?(km/n).toFixed(1)+" km":"—"],
    ["dias pedalados",dias.length],
    ["sequência",mx+" dia"+(mx===1?"":"s")]
  ].map(c=>'<div class="mini"><div class="lb">'+c[0]+'</div><div class="vl">'+c[1]+
    '</div></div>').join("");

  // Semanas do período — do mês escolhido, ou do ano inteiro.
  const base=D.filter(r=>r.a===A&&(!fm.value||r.m==+fm.value));
  const sm={};base.forEach(r=>{(sm[r.w]=sm[r.w]||{km:0,n:0}).km+=r.km;sm[r.w].n++;});
  const ks=Object.keys(sm).sort((x,y)=>x-y);
  const wmax=Math.max(...ks.map(s=>sm[s].km));
  $("hsem").innerHTML="Semanas"+(fm.value?' <small>de '+ML[+fm.value-1]+'</small>'
    :' <small>do ano</small>');
  $("sem").innerHTML=ks.length?ks.map(s=>{
    const on=fw.value==s;
    return '<div class="wk" data-w="'+s+'"><span class="rot"'+(on?' style="color:#1a1a19"':'')+
      '>semana '+s+'</span><div class="trk"><i style="width:'+(100*sm[s].km/wmax)+
      '%;background:'+(on?"#eb6834":sm[s].km===wmax?"#f0a58a":"#1baf7a")+'"></i></div>'+
      '<span class="val">'+br(sm[s].km)+' km · '+sm[s].n+' pedais</span></div>';
  }).join(""):'<div class="vazio">sem pedal no período</div>';
  document.querySelectorAll("[data-w]").forEach(e=>e.onclick=()=>{
    fw.value=fw.value==e.dataset.w?"":e.dataset.w;render();});

  // Meses — sempre o ano inteiro, senão a comparação perde sentido.
  const ms={};
  D.filter(r=>r.a===A).forEach(r=>{(ms[r.m]=ms[r.m]||{km:0,n:0}).km+=r.km;ms[r.m].n++;});
  const mmax=Math.max(...Object.values(ms).map(x=>x.km));
  $("mes").innerHTML=MS.map((nome,i)=>{
    const x=ms[i+1],on=fm.value==""+(i+1);
    if(!x)return '<div class="col" style="cursor:default">'+
      '<div style="height:3px;background:#e4e2db;border-radius:2px"></div>'+
      '<div class="l">'+nome+'</div></div>';
    return '<div class="col'+(on?' on':'')+'" data-m="'+(i+1)+'">'+
      '<div class="v">'+br(x.km)+'</div><div class="bar" style="height:'+
      Math.round(100*x.km/mmax)+'%;background:'+
      (on?"#eb6834":x.km===mmax?"#f0a58a":"#1baf7a")+'"></div>'+
      '<div class="l">'+nome+'</div><div class="p">'+x.n+'p</div></div>';
  }).join("");
  document.querySelectorAll("[data-m]").forEach(c=>c.onclick=()=>{
    fm.value=fm.value==c.dataset.m?"":c.dataset.m;fw.value="";
    opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");render();});

  $("comp").innerHTML=n?composicao(L):"";
  const alvo=$("verMes");
  alvo.style.display=fm.value?"inline":"none";
  alvo.href="mes.html?a="+A+"&m="+fm.value;
}
fa.oninput=()=>{opts(fm,meses(),v=>ML[v-1],"ano inteiro");
  fm.value=(+fa.value===ANO_ATUAL)?String(Math.max(...meses())):"";
  fw.value="";opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");render();};
fm.oninput=()=>{fw.value="";opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");render();};
fw.oninput=render;
render();
"""

SCRIPT_MES = """
const fa=$("fa"),fm=$("fm");
const meses=()=>[...new Set(D.filter(r=>r.a==+fa.value).map(r=>r.m))].sort((x,y)=>x-y);

opts(fa,anos(),v=>v);
// A tela inicial manda o mês clicado pela URL.
const q=new URLSearchParams(location.search);
fa.value=anos().includes(+q.get("a"))?q.get("a"):anos()[0];
opts(fm,meses(),v=>ML[v-1]);
fm.value=meses().includes(+q.get("m"))?q.get("m"):String(Math.max(...meses()));

function render(){
  const A=+fa.value,M=+fm.value;
  const L=D.filter(r=>r.a===A&&r.m===M);
  $("tit").innerHTML='<b>'+ML[M-1]+'</b><span>'+A+'</span>';
  history.replaceState(null,"","mes.html?a="+A+"&m="+M);

  if(!L.length){$("corpo").innerHTML='<div class="vazio">nenhum pedal neste mês</div>';return;}

  const n=L.length,km=L.reduce((s,r)=>s+r.km,0),mi=L.reduce((s,r)=>s+r.t,0),
        el=L.reduce((s,r)=>s+r.e,0);
  let h='<div class="minis">'+[
    ["km",br(km)],["pedais",n],["tempo",hm(mi)],["subida",br(el)+" m"],
    ["ritmo",(L.reduce((s,r)=>s+r.v,0)/n).toFixed(1)+" km/h"],
    ["média",(km/n).toFixed(1)+" km"]
  ].map(c=>'<div class="mini"><div class="lb">'+c[0]+'</div><div class="vl">'+c[1]+
    '</div></div>').join("")+'</div>';

  // Uma linha por cidade, com as datas em que passei por lá.
  const c={};
  L.forEach(r=>(r.r||[]).forEach(x=>{
    const nome=x[0];
    (c[nome]=c[nome]||{uf:x[1],novo:false,ds:[]}).ds.push(r.d);
    if((r.nv||[]).includes(nome))c[nome].novo=true;
  }));
  const ord=Object.entries(c).sort((a,b)=>b[1].ds.length-a[1].ds.length
    ||a[0].localeCompare(b[0]));
  const estreias=ord.filter(([,v])=>v.novo).length;
  h+='<h2>Por onde andei <small>'+ord.length+' cidade'+(ord.length===1?"":"s")+
    (estreias?' · '+estreias+' pela primeira vez':'')+'</small></h2>';
  h+=ord.length?'<div class="tabela"><table><thead><tr><th>cidade</th><th>uf</th>'+
    '<th style="text-align:right">vezes</th><th>datas</th></tr></thead><tbody>'+
    ord.map(([k,v])=>'<tr><td>'+k+(v.novo?'<span class="novo">1ª vez</span>':'')+
      '</td><td style="color:#6b6a65">'+v.uf+'</td>'+
      '<td style="text-align:right">'+v.ds.length+'</td><td>'+
      v.ds.map(d=>'<span class="dt">'+dia(d)+'</span>').join("")+'</td></tr>').join("")+
    '</tbody></table></div>':'<div class="vazio">sem cidade identificada</div>';

  h+='<h2>Composição</h2>'+composicao(L);

  h+='<h2>Os pedais</h2>'+L.map(r=>{
    let p='<div class="ped"><div class="linha">'+
      '<span class="dia">'+dia(r.d)+'</span>'+
      '<span class="nome">'+r.n+'</span>'+
      '<span class="km">'+r.km.toFixed(1)+'</span>'+
      '<span class="num" style="width:20px">km</span>'+
      '<span class="num" style="width:52px">'+hm(r.t)+'</span>'+
      '<span class="num" style="width:64px">'+r.v.toFixed(1)+' km/h</span>'+
      '<span class="num" style="width:58px">'+br(r.e)+' m</span>'+
      '<span style="width:136px;text-align:right">'+etiquetas(r)+'</span></div>';
    if(r.r&&r.r.length)p+='<div class="rota">'+r.r.map(x=>x[0]).join(" → ")+'</div>';
    return p+'</div>';
  }).join("");

  $("corpo").innerHTML=h;
}
fa.oninput=()=>{opts(fm,meses(),v=>ML[v-1]);
  fm.value=String(Math.max(...meses()));render();};
fm.oninput=render;
render();
"""

SCRIPT_HISTORICO = """
const fa=$("fa"),fm=$("fm"),fs=$("fs"),fp=$("fp"),fc=$("fc"),fq=$("fq"),fk=$("fk");
// Abre no ano corrente: 974 pedais de uma vez não é um ponto de partida útil,
// e o ano inteiro continua a um clique.
opts(fa,anos(),v=>v,"todos os anos");
fa.value=anos()[0];
opts(fm,[1,2,3,4,5,6,7,8,9,10,11,12],v=>ML[v-1],"todos os meses");
opts(fs,["estrada","misto","trilha"],v=>v,"todo piso");
opts(fp,["curto","medio","longo"],v=>v,"todo porte");
opts(fc,["rotina","exploracao"],v=>v==="rotina"?"só rotina":"só exploração",
     "rotina e exploração");

// Coluna pela qual ordenar: chave do registro, ou "" para a data.
let ord="",asc=false;
const COLUNAS=[["data",""],["pedal",null],["km","km"],["tempo","t"],
               ["km/h","v"],["subida","e"]];

function render(){
  [fm,fs,fp,fc].forEach(e=>e.parentElement.classList.toggle("on",!!e.value));
  const k=+fk.value;
  $("fko").textContent=k?"≥ "+k+" km":"todas";
  const q=fq.value.trim().toLowerCase();

  let L=D.filter(r=>
    (!fa.value||r.a==+fa.value)&&(!fm.value||r.m==+fm.value)&&
    (!fs.value||r.s===fs.value)&&(!fp.value||r.p===fp.value)&&
    (!fc.value||r.c===fc.value)&&r.km>=k&&
    (!q||r.n.toLowerCase().includes(q)));

  L=L.slice().sort((x,y)=>{
    const v=ord?x[ord]-y[ord]:x.d.localeCompare(y.d);
    return asc?v:-v;
  });

  const n=L.length,km=L.reduce((s,r)=>s+r.km,0),mi=L.reduce((s,r)=>s+r.t,0),
        el=L.reduce((s,r)=>s+r.e,0);
  $("res").innerHTML=[
    ["pedais",n],["km",br(km)],["elevação",br(el)+" m"],["tempo",hm(mi)],
    ["ritmo",n?(L.reduce((s,r)=>s+r.v,0)/n).toFixed(1)+" km/h":"—"],
    ["média",n?(km/n).toFixed(1)+" km":"—"]
  ].map(c=>'<div class="mini"><div class="lb">'+c[0]+'</div><div class="vl">'+
    c[1]+'</div></div>').join("");

  if(!n){$("tab").innerHTML='<div class="vazio">nenhum pedal com esses filtros</div>';
    $("total").textContent="";return;}

  let h='<div class="tabela rolagem"><table><thead><tr>';
  COLUNAS.forEach(([rot,chave])=>{
    const dir=chave&&chave!=="d"&&rot!=="pedal"?" dir":"";
    if(chave===null)h+='<th class="fixo">'+rot+'</th>';
    else h+='<th data-o="'+chave+'" class="'+dir.trim()+'">'+rot+
      (ord===chave?(asc?" ↑":" ↓"):"")+'</th>';
  });
  h+='<th class="fixo dir"></th></tr></thead><tbody>';

  L.forEach((r,i)=>{
    const p=r.d.split("-");
    h+='<tr class="abre" data-i="'+i+'">'+
      '<td style="color:#6b6a65;white-space:nowrap"><span class="ar">'+
      (r.r?"›":" ")+'</span> '+(+p[2])+" "+MS[+p[1]-1]+" "+p[0].slice(2)+'</td>'+
      '<td>'+r.n+'</td>'+
      '<td class="dir">'+r.km.toFixed(1)+'</td>'+
      '<td class="dir">'+hm(r.t)+'</td>'+
      '<td class="dir">'+r.v.toFixed(1)+'</td>'+
      '<td class="dir">'+br(r.e)+'</td>'+
      '<td class="dir">'+etiquetas(r)+'</td></tr>';
    if(r.r)h+='<tr class="rota" data-r="'+i+'" style="display:none"><td colspan="7">'+
      r.r.map(x=>x[0]).join(" → ")+'</td></tr>';
  });
  $("tab").innerHTML=h+'</tbody></table></div>';
  $("total").textContent=n+" de "+D.length+" pedais";

  document.querySelectorAll("th[data-o]").forEach(th=>th.onclick=()=>{
    const o=th.dataset.o;
    if(ord===o)asc=!asc;else{ord=o;asc=false;}
    render();
  });
  document.querySelectorAll("tr.abre").forEach(tr=>tr.onclick=()=>{
    const alvo=document.querySelector('tr.rota[data-r="'+tr.dataset.i+'"]');
    if(!alvo)return;
    const aberta=alvo.style.display!=="none";
    alvo.style.display=aberta?"none":"table-row";
    tr.classList.toggle("aberta",!aberta);
    tr.querySelector(".ar").textContent=aberta?"›":"⌄";
  });
}
[fa,fm,fs,fp,fc,fq,fk].forEach(e=>e.oninput=render);
$("limpar").onclick=()=>{
  [fa,fm,fs,fp,fc].forEach(e=>e.value="");
  fk.value=0;fq.value="";ord="";asc=false;render();
};
render();
"""


SCRIPT_ANOS = """
const me=$("me"),ate=$("ate");
const AN=[...new Set(D.map(r=>r.a))].sort((x,y)=>x-y);
// Uma cor por ano, do mais antigo ao mais recente. O ano corrente puxa o
// laranja da identidade, que é a cor de destaque no resto do painel.
const CA=["#c9c6bd","#9fd6c0","#5DCAA5","#378ADD","#eda100","#eb6834"];
const cor=i=>CA[(CA.length-AN.length+i+CA.length)%CA.length];

// Mês mais recente com pedal no ano corrente. Fixar setembro quebraria o
// rótulo assim que virasse o mês.
const ULTIMO=Math.max(...D.filter(r=>r.a===AN[AN.length-1]).map(r=>r.m));
$("rotAte").textContent="até "+ML[ULTIMO-1]+", em todos os anos";

// Agrega por ano e mês uma vez; os filtros só mudam a leitura.
const G={};
AN.forEach(a=>G[a]={});
D.forEach(r=>{
  const x=G[r.a][r.m]=G[r.a][r.m]||{n:0,km:0,el:0,t:0};
  x.n++;x.km+=r.km;x.el+=r.e;x.t+=r.t;
});

function render(){
  const k=me.value,lim=ate.checked?ULTIMO:12;
  const un={km:"km",n:"",el:"m",t:"h"}[k];
  const somaAno=a=>Object.entries(G[a]).filter(([m])=>m<=lim)
    .reduce((s,[,x])=>s+x[k],0);
  const totais=AN.map(somaAno),melhor=Math.max(...totais);

  let h='<div class="tabela"><table><thead><tr>';
  ["ano","total","pedais","média/pedal","meses","vs. anterior"].forEach((c,i)=>
    h+='<th'+(i?' style="text-align:right"':'')+'>'+c+'</th>');
  h+='</tr></thead><tbody>';

  AN.forEach((a,i)=>{
    const meses=Object.entries(G[a]).filter(([m])=>m<=lim);
    const v=totais[i];
    const np=meses.reduce((s,[,x])=>s+x.n,0);
    const km=meses.reduce((s,[,x])=>s+x.km,0);
    const ant=i?totais[i-1]:null;
    const dif=ant?Math.round(100*(v-ant)/ant):null;
    h+='<tr><td><span class="pt" style="background:'+cor(i)+'"></span>'+a+
      (v===melhor?'<span class="melhor">melhor</span>':'')+'</td>'+
      '<td style="text-align:right;font-weight:500">'+
      (k==="t"?br(v/60):br(v))+' <span class="un">'+un+'</span></td>'+
      '<td style="text-align:right">'+np+'</td>'+
      '<td style="text-align:right">'+(np?(km/np).toFixed(1):"—")+' km</td>'+
      '<td style="text-align:right;color:#6b6a65">'+meses.length+'</td>'+
      '<td style="text-align:right" class="'+(dif===null?"":dif>=0?"up":"down")+'">'+
      (dif===null?"—":(dif>0?"+":"")+dif+"%")+'</td></tr>';
  });
  $("tab").innerHTML=h+'</tbody></table></div>';

  let mx=0;
  AN.forEach(a=>Object.entries(G[a]).forEach(([m,x])=>{
    if(m<=lim)mx=Math.max(mx,x[k]);}));

  let g='<div class="gmes">';
  for(let m=1;m<=lim;m++){
    g+='<div class="m"><div class="pilha">';
    AN.forEach((a,i)=>{
      const x=G[a][m];
      g+='<i title="'+a+" "+MS[m-1]+': '+(x?br(k==="t"?x[k]/60:x[k]):0)+' '+un+
        '" style="height:'+(x?Math.max(2,100*x[k]/mx):1)+'%;background:'+
        (x?cor(i):"#e4e2db")+'"></i>';
    });
    g+='</div><div class="rot">'+MS[m-1]+'</div></div>';
  }
  $("graf").innerHTML=g+'</div>';
  $("leg").innerHTML=AN.map((a,i)=>'<span><i class="pt" style="background:'+
    cor(i)+';margin:0"></i>'+a+'</span>').join("");
}
me.oninput=render;ate.oninput=render;
render();
"""


SCRIPT_RECORDES = """
// Tudo é calculado na hora, a partir dos mesmos dados das outras telas: um
// recorde escrito à mão envelheceria no primeiro pedal novo.
const diaExt=s=>{const p=s.split("-");return (+p[2])+" "+MS[+p[1]-1]+" "+p[0];};
const topo=chave=>D.reduce((a,b)=>b[chave]>a[chave]?b:a);

const CARTOES=[
  ["🚴","maior distância","km",r=>r.km.toFixed(1),"km"],
  ["⚡","maior velocidade média","v",r=>r.v.toFixed(1),"km/h"],
  ["⛰","maior elevação","e",r=>br(r.e),"m"],
  ["🕐","mais tempo pedalando","t",r=>hm(r.t),""]
];

$("cartoes").innerHTML=CARTOES.map(([ic,rot,chave,fmt,un])=>{
  const r=topo(chave);
  return '<div class="c"><div class="ic">'+ic+'</div><div class="lb">'+rot+
    '</div><div class="vl">'+fmt(r)+' <span class="un">'+un+'</span></div>'+
    '<div class="qual">'+r.n+'</div>'+
    '<div class="quando">'+diaExt(r.d)+'</div></div>';
}).join("");

function agrupa(chave){
  const g={};
  D.forEach(r=>{
    const k=chave(r);
    const x=g[k]=g[k]||{km:0,n:0,a:r.a,m:r.m,w:r.w};
    x.km+=r.km;x.n++;
  });
  return Object.values(g);
}
const SEM=agrupa(r=>r.a+"-"+r.w), MES=agrupa(r=>r.a+"-"+r.m), ANO=agrupa(r=>r.a);
const maior=(lista,k)=>lista.reduce((a,b)=>b[k]>a[k]?b:a);

// Maior sequência de dias seguidos. Dois pedais no mesmo dia contam como um.
const dias=[...new Set(D.map(r=>r.d))].sort();
let ini=dias[0],recIni=dias[0],recFim=dias[0],seq=1,maxSeq=1;
for(let i=1;i<dias.length;i++){
  if((new Date(dias[i])-new Date(dias[i-1]))/864e5===1)seq++;
  else{seq=1;ini=dias[i];}
  if(seq>maxSeq){maxSeq=seq;recIni=ini;recFim=dias[i];}
}

const sw=maior(SEM,"km"), mk=maior(MES,"km"), mn=maior(MES,"n"),
      ak=maior(ANO,"km"), an=maior(ANO,"n");
const LINHAS=[
  ["maior distância numa semana",br(sw.km)+" km","semana "+sw.w+" de "+sw.a,sw.n+" pedais"],
  ["maior distância num mês",br(mk.km)+" km",ML[mk.m-1]+" de "+mk.a,mk.n+" pedais"],
  ["mais pedais num mês",mn.n+" pedais",ML[mn.m-1]+" de "+mn.a,br(mn.km)+" km"],
  ["maior distância num ano",br(ak.km)+" km",String(ak.a),ak.n+" pedais"],
  ["mais pedais num ano",an.n+" pedais",String(an.a),br(an.km)+" km"],
  ["maior sequência de dias",maxSeq+" dias",
   diaExt(recIni)+" a "+diaExt(recFim),""]
];

$("periodo").innerHTML='<div class="tabela"><table><tbody>'+LINHAS.map(r=>
  '<tr><td>'+r[0]+'</td>'+
  '<td style="text-align:right;font-weight:600;white-space:nowrap">'+r[1]+'</td>'+
  '<td style="color:#6b6a65;white-space:nowrap">'+r[2]+'</td>'+
  '<td style="text-align:right;color:#8a8880;white-space:nowrap">'+r[3]+'</td></tr>'
).join("")+'</tbody></table></div>';
"""


SCRIPT_MAPA = """
// Desenha os contornos do IBGE direto em SVG. Sem biblioteca de mapa e sem
// camada de imagem: a página continua funcionando sem internet, como as
// outras, e o traço combina com o resto do painel.
const EST=C.estados, MUN=C.municipios, VIS=C.visitadas;
const ufsComPedal=new Set(Object.keys(VIS).map(k=>k.split("|")[1]));
let estadoAberto=null, cidadeAberta=null;

// Projeção simples: achata a longitude pelo cosseno da latitude média, senão
// o Brasil sai esticado no sentido leste-oeste. Mercator seria exagero para
// a faixa de latitude de um país só.
function caixa(fs){
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  fs.forEach(f=>poligonos(f).forEach(p=>p.forEach(anel=>anel.forEach(([x,y])=>{
    if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;}))));
  return [x0,y0,x1,y1];
}
const poligonos=f=>f.t===1?[f.g]:f.g;

function desenha(fs,destaque,aoClicar,rotulo){
  const [x0,y0,x1,y1]=caixa(fs);
  const k=Math.cos((y0+y1)/2*Math.PI/180);
  const larg=(x1-x0)*k, alt=y1-y0;
  const px=([x,y])=>[((x-x0)*k).toFixed(3),(y1-y).toFixed(3)];
  const d=f=>poligonos(f).map(p=>p.map(anel=>
    "M"+anel.map(c=>px(c).join(",")).join("L")+"Z").join("")).join("");
  return '<svg viewBox="'+(-larg*.01)+' '+(-alt*.01)+' '+(larg*1.02)+' '+
    (alt*1.02)+'">'+fs.map((f,i)=>{
      const cls=destaque(f);
      return '<path class="'+cls+'" d="'+d(f)+'" data-i="'+i+'"><title>'+
        rotulo(f)+'</title></path>';
    }).join("")+'</svg>';
}

function brasil(){
  estadoAberto=null;cidadeAberta=null;
  const tot={};
  Object.entries(VIS).forEach(([k,v])=>{
    const uf=k.split("|")[1];
    const x=tot[uf]=tot[uf]||{cidades:0,pedais:0};
    x.cidades++;x.pedais=Math.max(x.pedais,v.n);
  });
  $("topo").innerHTML='<b>Brasil</b><span class="sep">·</span>'+
    '<span style="color:#8a8880">'+Object.keys(tot).length+
    ' estados · '+Object.keys(VIS).length+' cidades</span>';
  $("mapa").innerHTML=desenha(EST,
    f=>ufsComPedal.has(f.uf)?"tem":"vazio",
    null,
    f=>f.nome+(tot[f.uf]?" — "+tot[f.uf].cidades+" cidades":" — sem pedal"));
  $("lado").innerHTML='<h4>Estados</h4>'+
    Object.entries(tot).sort((a,b)=>b[1].cidades-a[1].cidades).map(([uf,x])=>
      '<div class="l" data-uf="'+uf+'">'+
      (EST.find(e=>e.uf===uf)||{nome:uf}).nome+
      '<span>'+x.cidades+' cidade'+(x.cidades>1?"s":"")+'</span></div>').join("")+
    '<p style="margin-top:.75rem">Clique num estado para ver as cidades.</p>';
  ligar();
}

function estado(uf){
  estadoAberto=uf;cidadeAberta=null;
  const fs=MUN.filter(m=>m.uf===uf);
  const nome=(EST.find(e=>e.uf===uf)||{nome:uf}).nome;
  const minhas=Object.entries(VIS).filter(([k])=>k.endsWith("|"+uf))
    .map(([k,v])=>({nome:k.split("|")[0],...v}))
    .sort((a,b)=>b.n-a.n||a.nome.localeCompare(b.nome));
  const porNome={};minhas.forEach(c=>porNome[c.nome]=c);
  const mx=Math.max(...minhas.map(c=>c.n));

  $("topo").innerHTML='<a id="voltar">Brasil</a><span class="sep">›</span>'+
    '<b>'+nome+'</b><span class="sep">·</span><span style="color:#8a8880">'+
    minhas.length+' de '+fs.length+' cidades</span>';
  $("mapa").innerHTML=desenha(fs,
    f=>porNome[f.nome]?(cidadeAberta===f.nome?"sel":"tem"):"vazio",
    null,
    f=>f.nome+(porNome[f.nome]?" — "+porNome[f.nome].n+" pedais":""));
  // Quem passei mais vezes fica mais escuro; a cor sozinha já conta a rotina.
  $("mapa").querySelectorAll("path.tem").forEach((p,i)=>{
    const c=porNome[fs.filter(f=>porNome[f.nome])[i].nome];
    if(c)p.style.fill=cidadeAberta?null:misturar(c.n/mx);
  });
  $("lado").innerHTML='<h4>Cidades</h4><div class="rol">'+minhas.map(c=>
    '<div class="l'+(cidadeAberta===c.nome?" on":"")+'" data-cid="'+c.nome+'">'+
    c.nome+'<span>'+c.n+'</span></div>').join("")+'</div>';
  ligar();
}

// Do verde claro ao escuro, conforme a frequência.
function misturar(f){
  const a=[159,214,192],b=[15,110,86];
  return "rgb("+a.map((v,i)=>Math.round(v+(b[i]-v)*f)).join(",")+")";
}

function cidade(nome){
  cidadeAberta=nome;
  const uf=estadoAberto;
  const info=VIS[nome+"|"+uf];
  estado(uf);
  const ps=D.filter(r=>(r.r||[]).some(x=>x[0]===nome));
  const km=ps.reduce((s,r)=>s+r.km,0);
  $("lado").insertAdjacentHTML("afterbegin",
    '<div style="background:#fff;border-radius:8px;padding:.75rem;margin-bottom:.9rem">'+
    '<h4 style="margin-bottom:.35rem">'+nome+'</h4>'+
    '<p>'+info.n+' pedal'+(info.n>1?"es":"")+' · '+br(km)+' km</p>'+
    '<p>desde '+dia(info.desde)+' de '+info.desde.slice(0,4)+'</p></div>');
  ligar();
}

function ligar(){
  const v=$("voltar");if(v)v.onclick=brasil;
  document.querySelectorAll("[data-uf]").forEach(e=>e.onclick=()=>estado(e.dataset.uf));
  document.querySelectorAll("[data-cid]").forEach(e=>e.onclick=()=>
    cidade(cidadeAberta===e.dataset.cid?null:e.dataset.cid)||0);
  $("mapa").querySelectorAll("path").forEach((p,i)=>{
    const t=p.querySelector("title").textContent.split(" — ")[0];
    if(p.classList.contains("vazio"))return;
    p.onclick=()=>estadoAberto?cidade(t):estado(
      (EST.find(e=>e.nome===t)||{}).uf);
  });
}

brasil();
"""


def navegacao(atual: str, gerados: set) -> str:
    itens = []
    for arquivo, rotulo in SECOES:
        pronto = arquivo in gerados
        classe = "on" if arquivo == atual else ("" if pronto else "off")
        alvo = arquivo if pronto else "#"
        itens.append(f'<a href="{alvo}" class="{classe}">{rotulo}</a>')
    return "<nav>" + "".join(itens) + "</nav>"


def ler(con, com_rota: bool = False) -> list:
    """Um registro por pedal, com chaves curtas para o JSON não inflar.

    `com_rota` acrescenta as cidades atravessadas na ordem de passagem e as que
    eram estreia. As telas de mês e histórico usam; na inicial seria peso morto.
    """
    linhas = con.execute("""
        SELECT data::DATE::VARCHAR       AS d,
               ano                       AS a,
               month(data)               AS m,
               week(data)                AS w,
               nome                      AS n,
               round(distancia_km, 1)    AS km,
               round(tempo_movimento_s / 60) AS t,
               round(velocidade_media_kmh, 1) AS v,
               ganho_elevacao_m          AS e,
               coalesce(tipo, 'rotina')  AS c,
               coalesce(porte, 'curto')  AS p,
               coalesce(piso, 'estrada') AS s,
               arquivo,
               cidade_nova
        FROM vw_pedais ORDER BY data
    """).fetchall()

    rotas = {}
    if com_rota:
        try:
            for arquivo, cidade, uf in con.execute(f"""
                SELECT arquivo, cidade, uf FROM cidades
                WHERE pontos > {MIN_PERMANENCIA}
                ORDER BY arquivo, entrada
            """).fetchall():
                rotas.setdefault(arquivo, []).append([cidade, uf])
        except duckdb.Error:
            pass

    saida = []
    for d, a, m, w, n, km, t, v, e, c, p, s, arquivo, novas in linhas:
        registro = {
            "d": d, "a": int(a), "m": int(m), "w": int(w),
            "n": (n or "").strip(), "km": float(km), "t": int(t),
            "v": float(v), "e": int(e or 0), "c": c, "p": p, "s": s,
        }
        if com_rota:
            rota = rotas.get(arquivo)
            if rota:
                registro["r"] = rota
            if novas:
                registro["nv"] = [x.strip() for x in novas.split(",")]
        saida.append(registro)

    return saida


def pagina(titulo: str, atual: str, gerados: set, corpo: str,
           dados: list, script: str, extra: str = "") -> str:
    embutido = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo}</title><style>{CSS}</style></head>
<body><div class="wrap">
{navegacao(atual, gerados)}
{corpo}
<footer>conatusride · {len(dados)} pedais · gerado do histórico do Strava</footer>
</div>
<script>const D={embutido};
{extra}
{COMUM}
{script}</script>
</body></html>"""


CORPO_INICIO = """<div class="filtros">
<span class="sel"><select id="fa"></select></span>
<span class="sel"><select id="fm"></select></span>
<span class="sel"><select id="fw"></select></span>
<span class="ctx" id="ctx"></span>
</div>
<div class="cards" id="cards"></div>
<div class="minis" id="minis"></div>
<h2 id="hsem">Semanas</h2>
<div id="sem"></div>
<h2>Meses <small>clique para filtrar</small></h2>
<div class="meses" id="mes"></div>
<h2>Composição <a id="verMes" style="font-size:12px;font-weight:400;margin-left:8px;color:#6b6a65">ver o mês em detalhe →</a></h2>
<div id="comp"></div>"""

CORPO_MES = """<div class="filtros">
<span class="sel"><select id="fa"></select></span>
<span class="sel"><select id="fm"></select></span>
</div>
<div class="tit" id="tit"></div>
<div id="corpo"></div>"""

CORPO_HISTORICO = """<div class="filtros">
<span class="sel"><select id="fa"></select></span>
<span class="sel"><select id="fm"></select></span>
<span class="sel"><select id="fs"></select></span>
<span class="sel"><select id="fp"></select></span>
<span class="sel"><select id="fc"></select></span>
<input class="busca" id="fq" placeholder="buscar pelo nome">
</div>
<div class="faixa-km">
<span>a partir de</span>
<input type="range" id="fk" min="0" max="120" step="5" value="0">
<span id="fko">todas</span>
<button class="limpar" id="limpar">limpar filtros</button>
</div>
<div class="minis" id="res"></div>
<h2>Os pedais <small>clique numa linha para ver a rota</small></h2>
<div id="tab"></div>
<p class="total" id="total"></p>"""


CORPO_ANOS = """<div class="filtros">
<span class="sel"><select id="me">
<option value="km">quilômetros</option>
<option value="n">pedais</option>
<option value="el">elevação</option>
<option value="t">horas</option>
</select></span>
<label class="chk"><input type="checkbox" id="ate"><span id="rotAte"></span></label>
</div>
<div id="tab"></div>
<h2>Mês a mês <small>uma cor por ano</small></h2>
<div id="graf"></div>
<div class="leg" id="leg"></div>"""


CORPO_RECORDES = """<h3>Num pedal só</h3>
<div class="rec" id="cartoes"></div>
<h3>Num período</h3>
<div id="periodo"></div>"""


CORPO_MAPA = """<div class="topo" id="topo"></div>
<div class="painel">
<div class="mapa" id="mapa"></div>
<div class="lado" id="lado"></div>
</div>"""


def main() -> None:
    if not BANCO.exists():
        raise FileNotFoundError(f"Não encontrei {BANCO}. Rode src/importar.py.")

    SAIDA.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(BANCO), read_only=True) as con:
        dados = ler(con)
        com_rota = ler(con, com_rota=True)

    contornos = RAIZ / "data" / "contornos.json"
    tem_mapa = contornos.exists()
    if not tem_mapa:
        print("aviso: data/contornos.json não existe — rode src/contornos.py")

    gerados = {"index.html", "mes.html", "historico.html", "anos.html",
               "recordes.html"}
    if tem_mapa:
        gerados.add("mapa.html")

    paginas = {
        "index.html": pagina("conatusride", "index.html", gerados,
                             CORPO_INICIO, dados, SCRIPT_INICIO),
        "mes.html": pagina("mês · conatusride", "mes.html", gerados,
                           CORPO_MES, com_rota, SCRIPT_MES),
        "historico.html": pagina("histórico · conatusride", "historico.html",
                                 gerados, CORPO_HISTORICO, com_rota,
                                 SCRIPT_HISTORICO),
        "anos.html": pagina("anos · conatusride", "anos.html", gerados,
                            CORPO_ANOS, dados, SCRIPT_ANOS),
        "recordes.html": pagina("recordes · conatusride", "recordes.html",
                                gerados, CORPO_RECORDES, dados,
                                SCRIPT_RECORDES),
    }

    if tem_mapa:
        paginas["mapa.html"] = pagina(
            "mapa · conatusride", "mapa.html", gerados, CORPO_MAPA, com_rota,
            SCRIPT_MAPA,
            extra="const C=" + contornos.read_text(encoding="utf-8") + ";",
        )

    for arquivo, html in paginas.items():
        (SAIDA / arquivo).write_text(html, encoding="utf-8")

    print(f"{len(dados)} pedais\n")
    for arquivo in paginas:
        kb = (SAIDA / arquivo).stat().st_size / 1024
        print(f"  {arquivo:16} {kb:5.0f} KB")
    print(f"\npronto — abra {SAIDA / 'index.html'}")


if __name__ == "__main__":
    main()
