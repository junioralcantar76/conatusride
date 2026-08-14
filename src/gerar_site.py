"""
conatusride — gerador das páginas HTML.

Lê o banco e escreve um site estático em docs/site/: uma página de visão geral
e uma por ano.

Os dados vão embutidos no HTML, não em arquivo separado: navegador aberto em
file:// bloqueia leitura de JSON local, e assim cada página funciona sozinha,
inclusive copiada para o celular.

Rode de novo depois de atualizar o banco para regerar tudo.

Ordem: importar.py -> pontos_partida.py -> metas.py -> tracos.py ->
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

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]

# Contexto de cada ano. Vem de docs/fases.md, não do Strava — é o que dá
# sentido aos números.
FASES = {
    2021: {
        "nome": "descoberta",
        "frase": "Início, sem pretensão.\nEntrar em forma, perder peso,\nsem noção da situação.",
        "texto": "Pedais curtos e frequentes. Era o começo de tudo.",
    },
    2022: {
        "nome": "imersão",
        "frase": "Entro no mundo do pedal,\nbem amador, em grupos\nde iniciantes.",
        "texto": "Gera uma vontade grande de pedalar, de conhecer e explorar. Ano de maior frequência — 4,9 pedais por semana, e nenhuma semana sem pedalar.",
    },
    2023: {
        "nome": "limites",
        "frase": "Já bem engajado.\nQueria ver meus limites,\nprovar que consigo.",
        "texto": "Ano de maior quilometragem e de maior elevação — 6,5 m de subida por km, o terreno mais duro de todos. É quando aparecem as viagens longas.",
    },
    2024: {
        "nome": "limbo",
        "frase": "Nova fase.\nJá entendia o mundo do pedal\ne fiquei procurando direção.",
        "texto": "A frequência cai, mas a distância média sobe. Menos pedais, mais longos.",
    },
    2025: {
        "nome": "distanciamento",
        "frase": "Criei certo receio.\nFicou chato por situações\nem grupo.",
        "texto": "Percebi interesses de colegas, fui criando distância e repensando o pedal. Mesmo assim, 50 das 52 semanas tiveram pedal.",
    },
    2026: {
        "nome": "escolha própria",
        "frase": "O pedal de grupo\nnão me acrescentava mais.\nEnjoei desse tipo de pedal.",
        "texto": "Acabou a fase dos pedais noturnos em Fortaleza com o grupo — o grupo enfraqueceu e eu percebi o risco: trânsito e violência. Resolvi estudar à noite. Último noturno da fase antiga: 18 de dezembro de 2025. No lugar dele, entrou o treino curto de manhã.",
    },
}

CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#faf9f7;color:#1a1a19;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:2rem 1.5rem 5rem}
nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:2.5rem}
nav a{font-size:13px;padding:5px 13px;border-radius:20px;text-decoration:none;color:#6b6a65}
nav a:hover{background:#efeee9;color:#1a1a19}
nav a.on{background:#1a1a19;color:#faf9f7}
h1{font-size:26px;font-weight:500;margin:0 0 .35rem}
.sub{font-size:14px;color:#6b6a65;margin:0 0 2.5rem}
.eyebrow{font-size:12px;letter-spacing:.09em;margin-bottom:8px}
.frase{font-family:Georgia,'Times New Roman',serif;font-size:31px;line-height:1.3;margin:0 0 12px;white-space:pre-line}
.texto{font-size:15px;color:#52514e;max-width:56ch;margin:0}
.nums{display:flex;align-items:flex-end;gap:2rem;flex-wrap:wrap;
padding:1.75rem 0;border-top:1px solid #e4e2db;border-bottom:1px solid #e4e2db;margin:2.25rem 0}
.n{font-family:Georgia,serif;line-height:1}
.n.hero{font-size:52px}
.n.big{font-size:32px}
.nl{font-size:12px;color:#8a8880;margin-top:4px}
h2{font-size:17px;font-weight:500;margin:2.5rem 0 1rem}
.head{display:flex;justify-content:space-between;align-items:baseline;margin:2.5rem 0 1rem}
.head h2{margin:0}
.head span{font-size:13px;color:#8a8880}
.bars{display:flex;align-items:flex-end;gap:6px;height:140px}
.bar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:100%}
.bar i{display:block;border-radius:4px 4px 0 0;min-height:3px;background:#1baf7a;font-style:normal}
.bar i.top{background:#eb6834}
.bv,.bl{font-size:11px;color:#8a8880;text-align:center}
.bv{margin-bottom:4px}.bl{margin-top:5px}
.wk{display:flex;align-items:center;gap:10px;margin-top:14px}
.wk b{font-size:12px;color:#8a8880;font-weight:400;width:62px;flex:none}
.wk div{display:flex;gap:2px;flex:1}
.wk s{flex:1;height:16px;border-radius:2px;text-decoration:none;display:block}
.yr{display:flex;align-items:center;gap:10px;margin-bottom:5px}
.yr a{width:120px;flex:none;text-decoration:none;color:#1a1a19}
.yr a small{display:block;font-size:11px;color:#8a8880}
.row{display:flex;align-items:baseline;gap:14px;padding:11px 0;border-top:1px solid #e4e2db;font-size:14px}
.row time{font-size:12px;color:#8a8880;width:52px;flex:none}
.row em{flex:1;font-style:normal}
.row b{font-family:Georgia,serif;font-size:19px;font-weight:400;width:64px;text-align:right}
.row u{font-size:12px;color:#8a8880;width:24px;text-decoration:none}
.row i{font-size:13px;color:#52514e;width:70px;text-align:right;font-style:normal}
.meta{display:flex;align-items:center;gap:10px;margin:8px 0}
.meta b{font-size:12px;color:#8a8880;font-weight:400;width:82px;flex:none}
.track{flex:1;height:8px;border-radius:4px;background:#efeee9;overflow:hidden}
.track i{display:block;height:100%;border-radius:4px;background:#1baf7a}
.meta u{font-size:12px;color:#52514e;width:40px;text-align:right;text-decoration:none}
.turno{flex:1;display:flex;height:8px;border-radius:4px;overflow:hidden;gap:2px}
.leg{display:flex;gap:16px;font-size:12px;color:#8a8880;margin-top:12px;flex-wrap:wrap}
.leg span{display:flex;align-items:center;gap:5px}
.sw{width:10px;height:10px;border-radius:2px;display:inline-block}
.grp{display:flex;align-items:baseline;gap:9px;margin:1.75rem 0 .25rem}
.grp b{font-size:16px;font-weight:500}
.grp small{font-size:13px;color:#8a8880}
.pct{font-size:13px;color:#8a8880;padding:0 0 4px 66px;line-height:1.6}
.cid{display:flex;flex-wrap:wrap;gap:7px;margin-top:.5rem}
.cid span{font-size:13px;padding:4px 11px;border-radius:20px;background:#efeee9;color:#52514e}
.cid span b{font-weight:400;color:#8a8880}
footer{margin-top:4rem;padding-top:1.25rem;border-top:1px solid #e4e2db;font-size:12px;color:#8a8880}
@media(max-width:640px){.frase{font-size:25px}.n.hero{font-size:42px}.n.big{font-size:26px}
.nums{gap:1.25rem}.yr a{width:88px}}
"""

RAMP = ["#E1F5EE", "#9FE1CB", "#5DCAA5", "#1D9E75", "#0F6E56"]
COR_TURNO = ["#eda100", "#eb6834", "#4a3aa7"]
NOME_TURNO = ["manhã", "tarde", "noite"]


def num(v) -> str:
    return f"{round(v):,}".replace(",", ".")


def cor_semana(km) -> str:
    if km is None:
        return "#efeee9"
    for limite, cor in zip((60, 110, 160, 210), RAMP):
        if km < limite:
            return cor
    return RAMP[4]


def navegacao(atual) -> str:
    itens = ['<a href="index.html"%s>visão geral</a>'
             % (' class="on"' if atual is None else "")]
    for ano in sorted(FASES):
        marca = ' class="on"' if ano == atual else ""
        itens.append(f'<a href="ano_{ano}.html"{marca}>{ano}</a>')
    return "<nav>" + "".join(itens) + "</nav>"


def pagina(titulo: str, atual, corpo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo} · conatusride</title><style>{CSS}</style></head>
<body><div class="wrap">{navegacao(atual)}{corpo}
<footer>conatusride · gerado a partir do histórico do Strava</footer>
</div></body></html>"""


def faixa_semanas(semanas: dict, rotulo: str = "semanas") -> str:
    celulas = []
    for s in range(1, 53):
        km = semanas.get(s)
        dica = f"Semana {s}: {num(km)} km" if km else f"Semana {s}: sem pedal"
        celulas.append(
            f'<s title="{dica}" style="background:{cor_semana(km)}"></s>'
        )
    return f'<div class="wk"><b>{rotulo}</b><div>{"".join(celulas)}</div></div>'


def barra_meta(km: float, meta) -> str:
    if not meta:
        return ""
    pct = round(100 * km / meta)
    return (
        f'<div class="meta"><b>meta {num(meta)}</b>'
        f'<div class="track"><i style="width:{min(100, pct)}%"></i></div>'
        f'<u>{pct}%</u></div>'
    )


def barra_turno(turnos) -> str:
    total = sum(turnos)
    if not total:
        return ""
    fatias = "".join(
        f'<div title="{NOME_TURNO[i]}: {n}" '
        f'style="width:{100 * n / total}%;background:{COR_TURNO[i]}"></div>'
        for i, n in enumerate(turnos) if n
    )
    return (
        f'<div class="meta"><b>turno</b><div class="turno">{fatias}</div>'
        f'<u>{round(100 * turnos[2] / total)}%</u></div>'
    )


def legenda_turno() -> str:
    itens = "".join(
        f'<span><i class="sw" style="background:{COR_TURNO[i]}"></i>{n}</span>'
        for i, n in enumerate(NOME_TURNO)
    )
    return f'<div class="leg">{itens}<span>% = pedais noturnos</span></div>'


# ---------------------------------------------------------------- consultas


def ler(con):
    dados = {}

    dados["totais"] = con.execute("""
        SELECT count(*) pedais, sum(distancia_km) km,
               sum(ganho_elevacao_m) elev, sum(tempo_movimento_s)/3600 horas
        FROM pedais
    """).fetchone()

    # tracos.py pode não ter rodado ainda; o site funciona sem as cidades.
    try:
        dados["cidades_total"] = con.execute(
            "SELECT count(DISTINCT cidade || uf), count(DISTINCT uf) FROM cidades"
        ).fetchone()
    except duckdb.Error:
        dados["cidades_total"] = (0, 0)

    dados["anos"] = con.execute("""
        SELECT p.ano, count(*) pedais, sum(p.distancia_km) km,
               sum(p.ganho_elevacao_m) elev, sum(p.tempo_movimento_s)/3600 horas,
               avg(p.velocidade_media_kmh) vel,
               count(DISTINCT week(p.data)) semanas, max(m.meta_km) meta,
               sum((hour(p.data) < 12)::INT) manha,
               sum((hour(p.data) BETWEEN 12 AND 18)::INT) tarde,
               sum((hour(p.data) > 18)::INT) noite
        FROM pedais p LEFT JOIN metas_ano m USING (ano)
        GROUP BY 1 ORDER BY 1
    """).df().to_dict("records")

    semanas = {}
    for ano, semana, km in con.execute("""
        SELECT ano, week(data), sum(distancia_km) FROM pedais GROUP BY 1, 2
    """).fetchall():
        semanas.setdefault(int(ano), {})[int(semana)] = float(km)
    dados["semanas"] = semanas

    meses = {}
    for ano, mes, pedais, km in con.execute("""
        SELECT ano, month(data), count(*), sum(distancia_km)
        FROM pedais GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall():
        meses.setdefault(int(ano), []).append((int(mes), int(pedais), float(km)))
    dados["meses"] = meses

    marcantes = {}
    # strftime devolveria o mês em inglês; monta a data com os nomes daqui.
    for ano, dia, mes, nome, km, elev, vel, arquivo in con.execute("""
        SELECT ano, day(data), month(data), nome,
               distancia_km, ganho_elevacao_m, velocidade_media_kmh, arquivo
        FROM (SELECT *, row_number() OVER
                (PARTITION BY ano ORDER BY distancia_km DESC) AS r FROM pedais)
        WHERE r <= 5 ORDER BY ano, r
    """).fetchall():
        quando = f"{int(dia)} {MESES[int(mes) - 1]}"
        marcantes.setdefault(int(ano), []).append(
            (quando, nome, km, elev, vel, arquivo)
        )
    dados["marcantes"] = marcantes

    tipos = {}
    listas = {}
    try:
        for ano, tipo, n in con.execute("""
            SELECT ano, tipo, count(*) FROM vw_pedais GROUP BY 1, 2
        """).fetchall():
            tipos.setdefault(int(ano), {})[tipo] = int(n)

        # Só os tipos que valem detalhar: os raros e memoráveis. Os pedais
        # curtos e médios são centenas e já aparecem nos agregados.
        for ano, tipo, dia, mes, nome, km, elev, vel, arq in con.execute("""
            SELECT ano, tipo, day(data), month(data), nome, distancia_km,
                   ganho_elevacao_m, velocidade_media_kmh, arquivo
            FROM (SELECT *, row_number() OVER (PARTITION BY ano, tipo
                    ORDER BY distancia_km DESC) AS r FROM vw_pedais)
            WHERE r <= 6 AND tipo IN ('evento', 'exploracao', 'pedal_longo')
            ORDER BY ano, tipo, distancia_km DESC
        """).fetchall():
            listas.setdefault(int(ano), {}).setdefault(tipo, []).append(
                (f"{int(dia)} {MESES[int(mes) - 1]}", nome, km, elev, vel, arq)
            )
    except duckdb.Error:
        pass
    dados["tipos"] = tipos
    dados["listas"] = listas

    cidades = {}
    percursos = {}
    try:
        for ano, cidade, uf, n in con.execute("""
            SELECT p.ano, c.cidade, c.uf, count(DISTINCT c.arquivo)
            FROM cidades c JOIN pedais p USING (arquivo)
            GROUP BY 1, 2, 3 ORDER BY 1, 4 DESC
        """).fetchall():
            cidades.setdefault(int(ano), []).append((cidade, uf, int(n)))

        # Percurso de cada pedal, na ordem real de passagem: `entrada` é o
        # índice do primeiro ponto dentro de cada cidade.
        for arquivo, percurso in con.execute("""
            SELECT arquivo, string_agg(cidade, ' → ' ORDER BY entrada)
            FROM cidades GROUP BY 1
        """).fetchall():
            percursos[arquivo] = percurso
    except duckdb.Error:
        pass
    dados["cidades"] = cidades
    dados["percursos"] = percursos

    return dados


# ---------------------------------------------------------------- páginas


def montar_indice(d) -> str:
    pedais, km, elev, horas = d["totais"]
    n_cidades, n_uf = d["cidades_total"]

    partes = [
        '<h1>conatusride</h1>',
        f'<p class="sub">Meu histórico de pedais, de 2021 a 2026</p>',
        '<div class="nums">',
        f'<div><div class="n hero">{num(km)}</div>'
        f'<div class="nl">quilômetros</div></div>',
        f'<div><div class="n big">{num(pedais)}</div>'
        f'<div class="nl">pedais</div></div>',
        f'<div><div class="n big">{num(elev)}</div>'
        f'<div class="nl">metros de subida</div></div>',
        f'<div><div class="n big">{num(horas)}</div>'
        f'<div class="nl">horas</div></div>',
        f'<div><div class="n big">{n_cidades}</div>'
        f'<div class="nl">cidades · {n_uf} estados</div></div>',
        "</div>",
        "<h2>Os anos</h2>",
    ]

    maior = max(a["km"] for a in d["anos"])
    for a in d["anos"]:
        ano = int(a["ano"])
        fase = FASES.get(ano, {"nome": ""})
        destaque = ' style="background:#eb6834"' if a["km"] == maior else ""
        largura = round(100 * a["km"] / maior)
        partes.append(
            f'<div class="yr"><a href="ano_{ano}.html">{ano}'
            f'<small>{fase["nome"]}</small></a>'
            f'<div class="track" style="height:22px;border-radius:4px">'
            f'<i style="width:{largura}%;border-radius:4px"{destaque}></i></div>'
            f'<u style="font-size:13px;color:#52514e;width:64px;'
            f'text-align:right;text-decoration:none">{num(a["km"])} km</u></div>'
        )

    partes.append('<div class="head"><h2>Semana a semana</h2>'
                  '<span>mais escuro, mais quilômetros</span></div>')
    for a in d["anos"]:
        ano = int(a["ano"])
        partes.append(faixa_semanas(d["semanas"].get(ano, {}), str(ano)))

    return "".join(partes)


ORDEM_TIPOS = ["pedal_curto", "pedal_medio", "pedal_longo",
               "treino", "evento", "exploracao"]

COR_TIPO = {"pedal_curto": "#B5D4F4", "pedal_medio": "#378ADD",
            "pedal_longo": "#185FA5", "treino": "#1baf7a",
            "evento": "#eb6834", "exploracao": "#eda100"}

LEGENDA_TIPO = {
    "evento": "trilhas e eventos festivos no interior",
    "exploracao": "férias no interior, rota nova",
    "pedal_longo": "os mais longos de Fortaleza e região",
}


def bloco_tipos(ano: int, d) -> str:
    conta = d["tipos"].get(ano, {})
    if not conta:
        return ""

    total = sum(conta.values())
    fatias, legenda = [], []
    for tipo in ORDEM_TIPOS:
        n = conta.get(tipo)
        if not n:
            continue
        cor = COR_TIPO[tipo]
        fatias.append(
            f'<div title="{tipo}: {n}" '
            f'style="width:{100 * n / total}%;background:{cor}"></div>'
        )
        legenda.append(
            f'<span><i class="sw" style="background:{cor}"></i>{tipo} {n}</span>'
        )

    partes = [
        "<h2>Tipos de pedal</h2>",
        f'<div class="turno" style="height:26px;border-radius:4px">'
        f'{"".join(fatias)}</div>',
        f'<div class="leg">{"".join(legenda)}</div>',
    ]

    for tipo in ("evento", "exploracao", "pedal_longo"):
        linhas = d["listas"].get(ano, {}).get(tipo, [])
        if not linhas:
            continue
        partes.append(
            f'<div class="grp"><i class="sw" style="background:{COR_TIPO[tipo]}">'
            f'</i><b>{tipo}</b><small>{LEGENDA_TIPO[tipo]}</small></div>'
        )
        for quando, nome, km, elev, vel, arquivo in linhas:
            partes.append(
                f'<div class="row"><time>{quando}</time><em>{nome.strip()}</em>'
                f'<b>{km:.1f}</b><u>km</u>'
                f'<i>{num(elev or 0)} m</i><i>{vel:.1f} km/h</i></div>'
            )
            percurso = d["percursos"].get(arquivo)
            if percurso:
                partes.append(f'<div class="pct">{percurso}</div>')

    return "".join(partes)


def montar_ano(ano: int, d) -> str:
    a = next(x for x in d["anos"] if int(x["ano"]) == ano)
    fase = FASES.get(ano, {"nome": "", "frase": "", "texto": ""})
    maior_km = max(x["km"] for x in d["anos"])
    recorde = " · recorde" if a["km"] == maior_km else ""

    partes = [
        f'<div class="eyebrow" style="color:#eb6834">'
        f'{fase["nome"].upper()}</div>',
        f'<p class="frase">{fase["frase"]}</p>',
        f'<p class="texto">{fase["texto"]}</p>',
        '<div class="nums">',
        f'<div><div class="n hero">{num(a["km"])}</div>'
        f'<div class="nl">quilômetros{recorde}</div></div>',
        f'<div><div class="n big">{num(a["elev"])}</div>'
        f'<div class="nl">metros de subida</div></div>',
        f'<div><div class="n big">{int(a["pedais"])}</div>'
        f'<div class="nl">pedais</div></div>',
        f'<div><div class="n big">{num(a["horas"])}</div>'
        f'<div class="nl">horas</div></div>',
        f'<div><div class="n big">{int(a["semanas"])}'
        f'<span style="font-size:17px;color:#8a8880">/52</span></div>'
        f'<div class="nl">semanas com pedal</div></div>',
        "</div>",
    ]

    meses = d["meses"].get(ano, [])
    if meses:
        pico = max(m[2] for m in meses)
        barras = []
        for mes, pedais, km in meses:
            classe = " top" if km == pico else ""
            barras.append(
                f'<div class="bar" title="{MESES[mes - 1]}: {num(km)} km em '
                f'{pedais} pedais"><div class="bv">{num(km)}</div>'
                f'<i class="{classe.strip()}" style="height:{round(100 * km / pico)}%"></i>'
                f'<div class="bl">{MESES[mes - 1]}</div></div>'
            )
        partes.append('<div class="head"><h2>Ao longo do ano</h2>'
                      f'<span>{num(a["km"])} km · meta {num(a["meta"])}</span></div>')
        partes.append(f'<div class="bars">{"".join(barras)}</div>')

    partes.append(faixa_semanas(d["semanas"].get(ano, {})))
    partes.append(barra_meta(a["km"], a["meta"]))
    partes.append(barra_turno([int(a["manha"]), int(a["tarde"]), int(a["noite"])]))
    partes.append(legenda_turno())

    partes.append(bloco_tipos(ano, d))

    cidades = d["cidades"].get(ano, [])
    if cidades:
        # Sem corte: as cidades visitadas uma única vez é que contam história.
        # As habituais o ciclista já sabe de cor.
        pilulas = "".join(
            f'<span>{c} <b>{n}</b></span>' for c, uf, n in cidades
        )
        partes.append(
            f'<h2>Cidades do ano</h2><p class="texto" style="margin-bottom:.75rem">'
            f'{len(cidades)} cidades atravessadas · o número é em quantos pedais</p>'
            f'<div class="cid">{pilulas}</div>'
        )

    return "".join(partes)


def main() -> None:
    if not BANCO.exists():
        raise FileNotFoundError(f"Não encontrei {BANCO}.")

    SAIDA.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(BANCO), read_only=True) as con:
        d = ler(con)

    (SAIDA / "index.html").write_text(
        pagina("visão geral", None, montar_indice(d)), encoding="utf-8"
    )
    print(f"docs/site/index.html")

    for a in d["anos"]:
        ano = int(a["ano"])
        (SAIDA / f"ano_{ano}.html").write_text(
            pagina(str(ano), ano, montar_ano(ano, d)), encoding="utf-8"
        )
        print(f"docs/site/ano_{ano}.html")

    print(f"\npronto — abra {SAIDA / 'index.html'} no navegador")


if __name__ == "__main__":
    main()
