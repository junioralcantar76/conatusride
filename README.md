# conatusride

Projeto pessoal de análise do meu histórico de pedais registrado no Strava.

O Strava cumpre bem seu papel na atividade individual, mas os dados que ele
guarda permitem extrair mais do que sua interface entrega. Este projeto reúne
esse histórico num ambiente próprio, onde eu possa analisar a evolução ao longo
do tempo e fazer minhas próprias perguntas.

## Stack

- Python
- DuckDB (armazenamento analítico, arquivo local)

## Estrutura

```
data/raw/          exportação do Strava, intocada (fora do Git)
data/              banco DuckDB (fora do Git)
src/               importação e normalização
notebooks/         exploração
docs/              visão do projeto e registro de decisões
```

## Dados

Os dados de pedais contêm coordenadas GPS de locais frequentes e **não são
versionados**. Ficam apenas na máquina local, ignorados pelo Git.

## Estado

Em construção — v1.

Documentos:

- [Visão do projeto](docs/visao.md)
- [Registro de decisões](docs/decisoes.md)
