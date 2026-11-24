# Painel

Seis telas, todas construídas. Os dados vão embutidos em cada página: navegador
aberto em `file://` bloqueia leitura de JSON local, e assim cada tela funciona
sozinha, inclusive copiada para o celular, sem internet.

Gerado por `src/gerar_site.py` em `docs/site/`.

## Por que é assim

As primeiras páginas foram feitas como **narrativa**: pouca informação por tela,
texto grande, história contada em ordem. Ficaram claras e não eram o que se usa
no dia a dia.

O que faz falta é **instrumento**: filtrar, cruzar, comparar, consultar. É o que
o BI anterior fazia e o que se usa de verdade.

O texto das fases continua no projeto, como camada de contexto sobre os números
— não mais como estrutura da página.

## As telas

### início — `index.html`

O ano corrente. Filtros de ano, mês e semana; dez indicadores (km, velocidade
média, pedais, horas, elevação, maior pedal, maior subida, média por pedal,
dias pedalados, sequência); barras de semana; gráfico mensal clicável;
composição por piso, porte e tipo.

Abre no mês mais recente com pedal. Ano fechado abre inteiro — dezembro não tem
nada de especial em retrospecto.

### mês — `mes.html`

Detalhe de um mês. Recebe o mês pela URL (`?a=2026&m=8`) — um arquivo por mês
seriam uns 60 para o mesmo resultado.

Traz "Por onde andei": uma linha por cidade, com as datas de cada passagem e
marca de primeira vez. Depois a composição e a lista de pedais com a rota.

### histórico — `historico.html`

Todos os pedais com filtros combináveis: ano, mês, piso, porte, tipo, busca por
nome, distância mínima. Tabela ordenável. A rota abre ao clicar na linha.

Abre no ano corrente.

### recordes — `recordes.html`

Quatro cartões para o recorde de um pedal só (distância, velocidade média,
elevação, tempo) e seis linhas para os de período (semana, mês, ano, sequência
de dias).

Tudo calculado na hora: um recorde escrito à mão envelheceria no primeiro pedal
novo.

### anos — `anos.html`

Tabela comparativa com variação sobre o ano anterior, seletor de medida e
gráfico mês a mês com uma cor por ano. Caixa "até o mês atual" para comparar no
mesmo ponto.

### mapa — `mapa.html`

Brasil em SVG, três níveis: estados → municípios → cidade. Sem biblioteca de
mapa e sem camada de imagem, para continuar funcionando offline.

Precisa de `data/contornos.json`, gerado uma vez por `src/contornos.py`.

## No dia a dia

Dois cliques em `atualizar.bat`, na raiz. Ele ativa o ambiente, busca os pedais
novos na API, classifica, regera as telas e abre o painel.

Para só olhar o painel, sem atualizar, abra `docs/site/index.html` — são
arquivos estáticos, não precisam de nada rodando.

## Carga completa

Só quando for refazer a base do zero. Baixar a exportação no Strava, apagar
`data/raw/` antes de extrair — senão os arquivos antigos ficam misturados e os
scripts os processam à toa — e rodar:

```
importar.py        exportação do Strava -> tabela pedais
pontos_partida.py  coordenada inicial de cada traçado
tracos.py          pontos por minuto + cidades atravessadas (~15 min)
metas.py           metas anuais
classificar.py     tipo, porte, piso
contornos.py       malha do IBGE -> contornos.json  (só quando mudar de estado)
gerar_site.py      as seis telas
```

## Ressalvas conhecidas

- **Modalidade** é uma só: o Strava classificou tudo como "Pedalada". O que faz
  sentido no lugar é o piso — estrada, misto, trilha —, marcado pelo nome.
- **Frequência cardíaca** existe em 6 pedais; o Strava gravou zero onde não
  havia sensor. Os campos ficam, e passam a valer quando a cinta voltar.
- **Potência fica fora.** Os watts estimados continuam na base mas não são
  exibidos: são cálculo do Strava a partir de peso e elevação, não medição.
  Medidor de cadência não resolve — cadência é rotação por minuto.
- **Elevação acima de 30 m/km é descartada** (decisão 23): três pedais em 974
  tinham erro de altímetro. A regra vale também para os pedais vindos da API.
- **Pedais vindos da API ficam sem clima, inclinação e distância em terra** — a
  API não entrega esses campos. Não afeta nenhuma análise.

## A fazer

- Aprimorar a tela de recordes.
- Rotas desenhadas no mapa, além das cidades. Os pontos por minuto já existem
  em `tracos`.
