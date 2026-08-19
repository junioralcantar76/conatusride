"""
conatusride — gerador do painel.

Lê o banco e escreve o painel em docs/site/. Por ora só a tela inicial; as
demais entram depois.

Os dados vão embutidos no HTML, não em arquivo separado: navegador aberto em
file:// bloqueia leitura de JSON local, e assim a página funciona sozinha,
inclusive copiada para o celular. São ~960 pedais, uns 60 KB.

Rode de novo depois de atualizar o banco.

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

SECOES = [
    ("index.html", "início"),
    ("mes.html", "mês"),
    ("historico.html", "histórico"),
    ("recordes.html", "recordes"),
    ("anos.html", "anos"),
    ("mapa.html", "mapa"),
]

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
nav a.off{opacity:.4;pointer-events:none}

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

footer{margin-top:3.5rem;padding-top:1rem;border-top:1px solid #e4e2db;font-size:12px;color:#8a8880}
@media(max-width:640px){.card .vl{font-size:22px}.wk .val{width:92px}.wk .rot{width:66px}}
"""

SCRIPT = """
const MS=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
const ML=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
          "setembro","outubro","novembro","dezembro"];
const br=n=>Math.round(n).toLocaleString("pt-BR");
const hm=m=>Math.floor(m/60)+"h"+String(Math.round(m%60)).padStart(2,"0");
const fa=document.getElementById("fa"),fm=document.getElementById("fm"),fw=document.getElementById("fw");

function anos(){return [...new Set(D.map(r=>r.a))].sort((x,y)=>y-x);}
function meses(){const L=D.filter(r=>r.a==+fa.value);
  return [...new Set(L.map(r=>r.m))].sort((x,y)=>x-y);}
function semanasDe(){const L=D.filter(r=>r.a==+fa.value&&(!fm.value||r.m==+fm.value));
  return [...new Set(L.map(r=>r.w))].sort((x,y)=>x-y);}

function opts(el,lista,rotulo,vazio){
  el.innerHTML='<option value="">'+vazio+'</option>'+
    lista.map(v=>'<option value="'+v+'">'+rotulo(v)+'</option>').join("");
}

anos().forEach(a=>fa.insertAdjacentHTML("beforeend",'<option>'+a+'</option>'));
fa.value=anos()[0];
opts(fm,meses(),v=>ML[v-1],"ano inteiro");
// O ano corrente abre no mês mais recente com pedal — a tela é sobre o agora.
// Ano fechado abre inteiro: dezembro não tem nada de especial em retrospecto.
const ANO_ATUAL=anos()[0];
if(+fa.value===ANO_ATUAL)fm.value=String(Math.max(...meses()));
opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");

function render(){
  [fm,fw].forEach(e=>e.parentElement.classList.toggle("on",!!e.value));
  const A=+fa.value;
  const L=D.filter(r=>r.a===A&&(!fm.value||r.m==+fm.value)&&(!fw.value||r.w==+fw.value));
  document.getElementById("ctx").textContent=
    fw.value?"semana "+fw.value+" · "+A : fm.value?ML[+fm.value-1]+" de "+A : A+" · ano inteiro";

  const n=L.length,km=L.reduce((s,r)=>s+r.km,0),mi=L.reduce((s,r)=>s+r.t,0),
        el=L.reduce((s,r)=>s+r.e,0);
  const dias=[...new Set(L.map(r=>r.d))].sort();
  let seq=dias.length?1:0,mx=seq;
  for(let i=1;i<dias.length;i++){
    seq=(new Date(dias[i])-new Date(dias[i-1]))/864e5===1?seq+1:1;
    mx=Math.max(mx,seq);
  }

  document.getElementById("cards").innerHTML=[
    ["🚴","Total Km",br(km),"km"],
    ["⏱","Vel. Média",n?(L.reduce((s,r)=>s+r.v,0)/n).toFixed(1):"0","km/h"],
    ["🚲","Pedais",n,""],
    ["🕐","Horas",hm(mi),""],
    ["⛰","Elevação",br(el),"m"]
  ].map(c=>'<div class="card"><div class="ic">'+c[0]+'</div><div class="lb">'+c[1]+
    '</div><div class="vl">'+c[2]+' <span class="un">'+c[3]+'</span></div></div>').join("");

  document.getElementById("minis").innerHTML=[
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
  document.getElementById("hsem").innerHTML="Semanas"+
    (fm.value?' <small>de '+ML[+fm.value-1]+'</small>':' <small>do ano</small>');
  document.getElementById("sem").innerHTML=ks.length?ks.map(s=>{
    const on=fw.value==s;
    return '<div class="wk" data-w="'+s+'"><span class="rot"'+(on?' style="color:#1a1a19"':'')+
      '>semana '+s+'</span><div class="trk"><i style="width:'+(100*sm[s].km/wmax)+
      '%;background:'+(on?"#eb6834":sm[s].km===wmax?"#f0a58a":"#1baf7a")+'"></i></div>'+
      '<span class="val">'+br(sm[s].km)+' km · '+sm[s].n+' pedais</span></div>';
  }).join(""):'<div style="font-size:13px;color:#8a8880">sem pedal no período</div>';
  document.querySelectorAll("[data-w]").forEach(e=>e.onclick=()=>{
    fw.value=fw.value==e.dataset.w?"":e.dataset.w;render();});

  // Meses — sempre o ano inteiro, senão a comparação perde sentido.
  const ms={};D.filter(r=>r.a===A).forEach(r=>{(ms[r.m]=ms[r.m]||{km:0,n:0}).km+=r.km;ms[r.m].n++;});
  const mmax=Math.max(...Object.values(ms).map(x=>x.km));
  document.getElementById("mes").innerHTML=MS.map((nome,i)=>{
    const x=ms[i+1],on=fm.value==""+(i+1);
    if(!x)return '<div class="col" style="cursor:default">'+
      '<div style="height:3px;background:#e4e2db;border-radius:2px"></div>'+
      '<div class="l">'+nome+'</div></div>';
    return '<div class="col'+(on?' on':'')+'" data-m="'+(i+1)+'">'+
      '<div class="v">'+br(x.km)+'</div>'+
      '<div class="bar" style="height:'+Math.round(100*x.km/mmax)+'%;background:'+
      (on?"#eb6834":x.km===mmax?"#f0a58a":"#1baf7a")+'"></div>'+
      '<div class="l">'+nome+'</div><div class="p">'+x.n+'p</div></div>';
  }).join("");
  document.querySelectorAll("[data-m]").forEach(c=>c.onclick=()=>{
    fm.value=fm.value==c.dataset.m?"":c.dataset.m;
    fw.value="";opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");render();});

  const dims=[
    ["piso","s",{estrada:"#B5D4F4",misto:"#eda100",trilha:"#eb6834"}],
    ["porte","p",{curto:"#B5D4F4",medio:"#378ADD",longo:"#185FA5"}],
    ["tipo","c",{rotina:"#B5D4F4",exploracao:"#1baf7a"}]
  ];
  document.getElementById("comp").innerHTML=dims.map(([nome,k,cores])=>{
    const q={};L.forEach(r=>q[r[k]]=(q[r[k]]||0)+1);
    const kk=Object.keys(cores).filter(x=>q[x]);
    if(!kk.length)return"";
    return '<div class="dim"><div class="t">'+nome+'</div><div class="faixa">'+
      kk.map(x=>'<div title="'+x+': '+q[x]+'" style="width:'+(100*q[x]/n)+
        '%;background:'+cores[x]+'"><span>'+x+'</span><span class="q">'+q[x]+
        '</span></div>').join("")+'</div></div>';
  }).join("");
}

fa.oninput=()=>{opts(fm,meses(),v=>ML[v-1],"ano inteiro");
  fm.value=(+fa.value===ANO_ATUAL)?String(Math.max(...meses())):"";
  fw.value="";
  opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");render();};
fm.oninput=()=>{fw.value="";opts(fw,semanasDe(),v=>"semana "+v,"todas as semanas");render();};
fw.oninput=render;
render();
"""


def navegacao(atual: str) -> str:
    itens = []
    for arquivo, rotulo in SECOES:
        existe = (SAIDA / arquivo).exists() or arquivo == atual
        classe = "on" if arquivo == atual else ("" if existe else "off")
        alvo = arquivo if existe else "#"
        itens.append(f'<a href="{alvo}" class="{classe}">{rotulo}</a>')
    return "<nav>" + "".join(itens) + "</nav>"


def ler(con) -> list:
    """Um registro por pedal, com nomes curtos para o JSON não inflar."""
    linhas = con.execute("""
        SELECT data::DATE::VARCHAR      AS d,
               ano                      AS a,
               month(data)              AS m,
               week(data)               AS w,
               nome                     AS n,
               round(distancia_km, 1)   AS km,
               round(tempo_movimento_s / 60) AS t,
               round(velocidade_media_kmh, 1) AS v,
               ganho_elevacao_m         AS e,
               coalesce(tipo, 'rotina') AS c,
               coalesce(porte, 'curto') AS p,
               coalesce(piso, 'estrada') AS s
        FROM vw_pedais ORDER BY data
    """).fetchall()

    return [
        {"d": d, "a": int(a), "m": int(m), "w": int(w), "n": (n or "").strip(),
         "km": float(km), "t": int(t), "v": float(v), "e": int(e or 0),
         "c": c, "p": p, "s": s}
        for d, a, m, w, n, km, t, v, e, c, p, s in linhas
    ]


def inicio(dados: list) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>conatusride</title><style>{CSS}</style></head>
<body><div class="wrap">
{navegacao("index.html")}
<div class="filtros">
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
<h2>Composição</h2>
<div id="comp"></div>
<footer>conatusride · {len(dados)} pedais · gerado do histórico do Strava</footer>
</div>
<script>const D={json.dumps(dados, ensure_ascii=False, separators=(",", ":"))};
{SCRIPT}</script>
</body></html>"""


def main() -> None:
    if not BANCO.exists():
        raise FileNotFoundError(f"Não encontrei {BANCO}. Rode src/importar.py.")

    SAIDA.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(BANCO), read_only=True) as con:
        dados = ler(con)

    destino = SAIDA / "index.html"
    destino.write_text(inicio(dados), encoding="utf-8")

    tamanho = destino.stat().st_size / 1024
    print(f"{len(dados)} pedais · {tamanho:.0f} KB")
    print(f"pronto — abra {destino}")


if __name__ == "__main__":
    main()
