"""
conatusride — cadastro de eventos.

Acrescenta uma linha a docs/eventos.csv, perguntando os campos no terminal.

Evento não sai de regra automática: existe trilha dentro da região de rotina, e
o que separa evento de pedal comum é ter data marcada e organização — algo que
o dado do Strava não sabe. Este arquivo é a marcação manual, e tem a última
palavra na classificação.

Depois de cadastrar, rode src/classificar.py para a marcação valer.

Uso:
    python src/eventos.py           cadastra um evento
    python src/eventos.py --listar  mostra os já cadastrados
"""

from pathlib import Path
import csv
import sys

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "docs" / "eventos.csv"
BANCO = RAIZ / "data" / "conatusride.duckdb"

CAMPOS = ["evento", "cidade_local", "data"]


def ler() -> list:
    if not CSV.exists():
        return []
    with CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def escrever(linhas: list) -> None:
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(sorted(linhas, key=lambda x: x["data"]))


def listar() -> None:
    linhas = ler()
    if not linhas:
        print("nenhum evento cadastrado")
        return
    print(f"{len(linhas)} evento(s):\n")
    for linha in sorted(linhas, key=lambda x: x["data"]):
        local = f" · {linha['cidade_local']}" if linha["cidade_local"] else ""
        print(f"  {linha['data']}  {linha['evento']}{local}")


def pedal_da_data(data: str):
    """Confere se existe pedal naquela data, para evitar erro de digitação."""
    if not BANCO.exists():
        return None
    try:
        with duckdb.connect(str(BANCO), read_only=True) as con:
            return con.execute(
                "SELECT nome, round(distancia_km, 1) FROM pedais "
                "WHERE data::DATE = ?", [data]
            ).fetchall()
    except duckdb.Error:
        return None


def perguntar(rotulo: str, obrigatorio: bool = True) -> str:
    while True:
        valor = input(f"{rotulo}: ").strip()
        if valor or not obrigatorio:
            return valor
        print("  (obrigatório)")


def cadastrar() -> None:
    print("Novo evento — enter em branco cancela\n")

    evento = perguntar("Evento", obrigatorio=False)
    if not evento:
        print("cancelado")
        return

    local = perguntar("Cidade/Local", obrigatorio=False)

    while True:
        data = perguntar("Data (AAAA-MM-DD)")
        if len(data) == 10 and data[4] == "-" and data[7] == "-":
            break
        print("  formato: 2026-07-05")

    pedais = pedal_da_data(data)
    if pedais is None:
        pass
    elif not pedais:
        print(f"\n  aviso: nenhum pedal em {data}")
        if input("  cadastrar assim mesmo? (s/N) ").strip().lower() != "s":
            print("cancelado")
            return
    else:
        for nome, km in pedais:
            print(f"\n  pedal encontrado: {nome} · {km} km")

    linhas = ler()
    if any(l["data"] == data for l in linhas):
        print(f"\n  já existe evento em {data}")
        if input("  acrescentar outro? (s/N) ").strip().lower() != "s":
            print("cancelado")
            return

    linhas.append({"evento": evento, "cidade_local": local, "data": data})
    escrever(linhas)

    print(f"\ngravado em docs/eventos.csv ({len(linhas)} eventos)")
    print("rode src/classificar.py para a marcação valer")


def main() -> None:
    if "--listar" in sys.argv:
        listar()
    else:
        cadastrar()


if __name__ == "__main__":
    main()
