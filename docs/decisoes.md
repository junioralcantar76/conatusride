# Registro de decisões

Cada decisão com a razão. Ordem cronológica.

---

## 1. Exportação primeiro, API depois

**Decisão** — A v1 usa apenas a exportação do Strava. A API entra na v2, para
buscar os pedais posteriores à última carga.

**Razão** — A exportação entrega 100% do histórico sem OAuth, sem token
expirando e sem limite de requisição. Misturar autenticação com a carga inicial
gastaria tempo brigando com o OAuth em vez de olhar os dados.

**Consequência** — O modelo de dados já nasce preparado para a API: identificador
estável por pedal e camada de normalização separada da leitura do arquivo, para
que as duas fontes desemboquem no mesmo formato.

---

## 2. DuckDB como armazenamento analítico

**Decisão** — DuckDB.

**Razão** — É feito para consulta analítica sobre histórico, que é exatamente o
uso aqui. Não exige servidor: um arquivo e um `pip install`. Lê CSV e Parquet
direto, o que encaixa com a carga vinda de arquivos.

**Alternativas descartadas** — SQLite (voltado a transação, não análise);
arquivos soltos com pandas (perde SQL).

**Trade-off** — Menos conhecido que SQLite, logo menos material pronto quando
travar.

---

## 3. Python

**Decisão** — Python.

**Razão** — DuckDB, pandas e leitura de GPX são maduros nesse ecossistema.

---

## 4. Dados fora do Git

**Decisão** — Repositório público com o código. Exportação e banco ignorados
pelo Git.

**Razão** — Os pedais contêm coordenadas GPS de locais frequentes. Publicá-las
expõe endereços.

---

## 5. Duas camadas de dado

**Decisão** — `raw` guarda a exportação como veio, intocada. A camada analítica
guarda o dado normalizado.

**Razão** — Se uma regra de normalização mudar, dá para reprocessar tudo a
partir do bruto, sem depender de nova exportação.

---

## 6. Recorte temporal a partir de 2021

**Decisão** — Só entram pedais de 2021 em diante.

**Razão** — Há um único registro de 2018, com quase três anos de lacuna depois
dele. Mantê-lo distorceria qualquer análise temporal. O histórico contínuo
começa em junho de 2021.

---

## 7. Clima incluído no escopo

**Decisão** — Os campos de clima entram na base, embora não estivessem previstos.

**Razão** — Estão preenchidos em 887 dos 961 pedais e não custam nada para
carregar. Se surgir uma pergunta sobre eles, o dado já está lá.

---

## 8. Aproveitar toda coluna com dado

**Decisão** — Entra tudo que estiver preenchido; sai o que estiver 100% vazio.

**Razão** — Evita reprocessar quando surgir uma curiosidade nova. As colunas
vazias são de outros esportes (natação, escalada, musculação) e não se aplicam.

**Ressalva** — "Preenchido" não é o mesmo que "com dado". O Strava grava zero
onde não havia sensor: as 318 cadências e 314 das 320 frequências cardíacas são
zeros. Cadência foi descartada; FC ficou, com valor real em apenas 6 pedais.

---

## 9. Nomes de coluna em minúsculo com unidade no sufixo

**Decisão** — `distancia_m`, `velocidade_media_kmh`, `ganho_elevacao_m`.

**Razão** — Os nomes originais têm acento, espaço e ponto (`Velocidade máx.`,
`Distância.1`), o que atrapalha em SQL. E o CSV traz colunas duplicadas em
unidades diferentes — `Distância` em km com vírgula, `Distância.1` em metros.
O sufixo elimina a ambiguidade.

---

## 10. Recriar a tabela a cada importação

**Decisão** — O script apaga e recria a tabela `pedais` toda vez que roda.

**Razão** — A fonte é um arquivo único e completo. Recriar é mais simples e mais
seguro do que mesclar registros, e garante idempotência sem lógica extra.

**Revisar quando** — A API entrar na v2. Aí passa a haver carga incremental e
essa estratégia não serve mais.

---

## 11. O projeto acompanha desempenho, mas não é sobre otimizá-lo

**Decisão** — As perguntas do projeto são sobre enxergar o conjunto e ligar os
números ao contexto de vida, não sobre maximizar métricas de treino.

**Razão** — Nunca houve pedal para competir. As médias incluem paradas para
comer, hidratar e resolver problemas mecânicos, e pedalar em grupo muda o ritmo.
Tratar essas médias como indicador de forma levaria a conclusões erradas.

**Consequência** — Existe um documento de fases (`fases.md`) registrando o
contexto ano a ano. É ele que dá sentido às variações nos dados.

---

## 12. Ponto de partida extraído dos arquivos de traçado

**Decisão** — Um script separado (`src/pontos_partida.py`) lê a coordenada
inicial de cada arquivo em `data/raw/activities/` e grava na tabela
`pontos_partida`, ligada a `pedais` pelo nome do arquivo.

**Razão** — O `activities.csv` não traz coordenada nenhuma. Sem isso, separar
pedal urbano de evento ou viagem dependeria de adivinhar pelo nome da atividade.
Com a coordenada, sai por distância medida.

**Escopo** — Isto antecipa parte da v2, mas lê apenas o ponto inicial, não o
traçado completo. A análise de streams segue fora da v1.

**Formatos** — 596 arquivos `.fit.gz` e 361 `.gpx`. O script trata os dois.

---

## 13. Coordenada zerada é descartada

**Decisão** — Coordenada com latitude e longitude ambas abaixo de 1 grau é
tratada como ausente, e o script busca o primeiro ponto real do traçado.

**Razão** — Cerca de 36% dos arquivos FIT gravam `start_position` como zero em
vez de omitir o campo. Zero é uma coordenada válida em tese — fica no Golfo da
Guiné — e a primeira execução do script colocou 212 pedais a mais de 4.000 km
de Fortaleza. Depois da correção, restaram 28 pedais acima de 300 km, que são
as férias na Paraíba.

**Lição** — Vale desconfiar de qualquer resultado geográfico que não faça
sentido narrativo antes de aceitá-lo como padrão.

---

## 14. Duas classificações independentes

**Decisão** — Os pedais recebem dois campos distintos:

- **tipo**, por onde começaram e por contexto: `exploracao` (300+ km de
  Fortaleza), `evento` (50–300 km), `treino` (curtos de 2026), `local_longo`,
  `local_medio`, `local_curto`.
- **porte**, pela escala de esforço percebido: `longao` acima de 79 km,
  `medio` de 50 a 78, `curto` abaixo de 50.

**Razão** — Medem coisas diferentes. Um pedal pode ser rotina e longão ao mesmo
tempo. A escala de porte é a percepção atual e, aplicada ao passado, mostra o
crescimento: 2021 não tem nenhum médio ou longão.

**Pendente** — Ainda não estão fixados na base; hoje são calculados em consulta.

---

## 15. Classificação em três campos — pendente

**Decisão** — Substituir o campo único `tipo` por três campos independentes. Um
pedal pode ser evento *e* exploração ao mesmo tempo (Guaramiranga, 2023), e uma
gaveta só não comporta isso.

| Campo | O que responde | Valores |
|---|---|---|
| `tipo` | que espécie de pedal foi | rotina, treino, evento, viagem |
| `porte` | qual o tamanho | curto, medio, longo |
| `exploracao` | teve cidade inédita? | sim, não |

**Porte** — curto abaixo de 50 km, médio de 50 a 74, longo de 75 em diante.
Independe do tipo: Pindoretama e volta dá 100 km e é rotina de porte longo. Uma
escala só, valendo para os dois campos, para nunca se contradizerem.

**Exploração** — marca sim/não: o pedal atravessou ao menos uma cidade onde eu
nunca tinha pedalado até aquela data. Não é sobre rota nova nem sobre distância,
é sobre estar fora da rotina — uma trilha na região metropolitana conta. Vale
para qualquer tipo. Calculável: as cidades têm data, basta percorrer em ordem
cronológica.

**Status** — definido, não aplicado. Vale revisar antes de mexer no código.

---

## 16. Região metropolitana em vez de raio em km — pendente

**Decisão** — `rotina` passa a ser definida pelos 19 municípios da Região
Metropolitana de Fortaleza, não por distância até o centro.

**Razão** — Raio de 50 km separa mal. Baturité fica a 77 km e não é
metropolitana; São Gonçalo do Amarante fica a 40 e é.

**Efeito a conferir** — Paracuru e Trairi são metropolitanas por lei, mas 131 km
até lá talvez não seja "rotina" no sentido vivido. Checar a lista contra a
percepção antes de aplicar.

**Viagem x evento** — viagem é 2 ou mais pedais em dias consecutivos com base no
lugar (Ubajara, dois dias seguidos). Dia isolado seria evento — mas ver a
decisão 17.

---

## 17. Evento é marcação manual — pendente

**Decisão** — Evento não sai de regra automática. Fica registrado à mão em
`docs/eventos.csv`.

**Razão** — Evento não se define por geografia: existe trilha em Caucaia, dentro
da região metropolitana, que é evento. O que separa evento de rotina é ter data
marcada e organização — e isso o dado do Strava não sabe. As pistas disponíveis
(a palavra "trilha" no nome, ritmo baixo de 12 a 13 km/h contra 17 na rotina)
não são confiáveis sozinhas.

**Formato** — três campos:

```
evento,cidade_local,data
Guaramiranga,Guaramiranga CE,2023-07-09
Trilha da Banana,Baturité CE,2022-05-15
```

**Preenchimento** — por um script que pergunta os campos no terminal e grava a
linha. Formulário de verdade exigiria servidor; o navegador sozinho não escreve
arquivo, e isso mudaria a arquitetura à toa.

**Onde fica** — em `docs/`, não em `data/`. Não é dado do Strava, é conhecimento
meu, mesma natureza do `fases.md`. Por isso vai para o Git, ao contrário dos
dados. Com os anos, vira o registro dos eventos de que participei.

**Partida** — gerar um rascunho com os candidatos prováveis para revisão, em vez
de preencher do zero. São uns 20 a 30 em cinco anos.

---

## 18. Painel é instrumento, não narrativa

**Decisão** — Reconstruir o painel em torno de filtros e densidade de
informação, em vez de páginas narrativas com uma fase por tela.

**Razão** — As primeiras páginas foram feitas como narrativa: pouca informação
por tela, texto grande, história contada em ordem. Ficaram claras e não eram o
que se usa no dia a dia. O que faz falta é poder filtrar e cruzar — ver como foi
a semana, como está o mês — que é o que o BI anterior fazia.

**Consequência técnica** — Filtro combinável exige os dados no navegador, não o
resultado pré-somado. Os 961 pedais vão embutidos no HTML (~60 KB) e a página
recalcula na hora. Isso substitui a arquitetura em que cada página trazia
números já agregados.

**Escopo** — Seis blocos definidos em `docs/painel.md`: visão do ano, evolução
mensal, histórico filtrável, recordes, comparação entre anos e mapa. O histórico
filtrável vem primeiro, por ser a fundação dos outros.

**O texto das fases** continua no projeto, como camada de contexto sobre os
números — não mais como estrutura da página.

---

## 19. Classificação em três dimensões

**Decisão** — Três dimensões independentes, cada uma medindo uma coisa só:

| Dimensão | Valores | Mede |
|---|---|---|
| `porte` | curto, medio, longo | o tamanho |
| `piso` | estrada, misto, trilha | o terreno |
| `tipo` | exploracao, rotina | se teve cidade inédita |

**Razão** — A versão anterior tinha rotina, treino, evento e viagem num campo
só, e elas se sobrepunham: uma viagem pode conter um evento, e treino é uma
rotina com outra intenção. Um pedal não cabia numa gaveta só.

**Resultado** — 34 explorações em cinco anos (3 em 2021, pico de 10 em 2022,
depois 4 a 6 por ano). Piso: 923 estrada, 20 misto, 18 trilha. As assinaturas
não se confundem — exploração tem 51,9 km e 9,1 m/km contra 30,1 e 4,8 da
rotina; trilha roda a 12,3 km/h contra 16,0 da estrada.

**Saíram do modelo** — treino, evento, viagem, a região de rotina, o
`docs/eventos.csv` e o `src/eventos.py`.

---

## 20. Porte com propósito

| Porte | Distância | O que é |
|---|---|---|
| curto | até 40 km | pedal rápido, treino, deslocamento |
| medio | 41 a 75 km | pedal regular |
| longo | acima de 75 km | pedal de resistência |

**Razão da mudança** — O corte anterior era 50 e 75. Com 40, o Maluaga (41 km)
sobe para médio, separado dos treinos de 15 km, que é onde ele pertence.

---

## 21. Piso — marcação pelo nome

**Definições do ciclista**

- **trilha** — maior parte da rota fora do asfalto: terra, calçamento ou
  singletrack. Pode atravessar cidade no caminho.
- **estrada** — predominância de asfalto ou rodovia. É o padrão.
- **misto** — alterna os dois, sem predominância clara.

**Como identificar** — pelo nome do pedal. O termo "trilha" sempre é usado, e de
2026 em diante "misto" também será. Para trás, os casos foram levantados ano a
ano com o ciclista e estão em listas de exceção no código.

**O dado do Strava não serve** — `distancia_terra_m` marca 1% na Trilha Apuiarés,
que foi quase toda em terra, e 0% no Posto Arizona, que é asfalto puro. Dois
pedais do mesmo bloco de férias aparecem com 0% e 47%. As estradas dessas
regiões não constam como não pavimentadas no mapa deles. Não usar nem como
complemento.

**Exceções registradas** — 19 mistos levantados um a um (2021 sem nenhum, 2023
sem nenhum); "Terra na veia" (2022) é trilha sem a palavra no nome; "Aventura:
Cofeco, trilha do mangue, Mangabeira" tem "trilha" no nome mas é rotina de
domingo com um trecho curto de trilha — é misto, não trilha.

---

## 22. Exploração — permanência mínima de 5 minutos

**Decisão** — Uma cidade só conta como explorada com mais de 5 minutos de
permanência. Amostramos um ponto por minuto, então são 5 pontos.

**Razão** — Em "Ceará - Paraíba" cruzei São João do Rio do Peixe em um minuto,
na estrada entre Santa Helena e Bom Jesus. Entrei no território, mas não conheci
nada.

**Por que 5 e não 3** — O resultado hoje é idêntico (só Horizonte, São João do
Rio do Peixe e Pentecoste ficam abaixo, todas com 1 ou 2 minutos). O corte foi
escolhido pelo que significa: a 20 km/h, 5 minutos são quase 2 km — atravessar
a cidade, não raspar a borda. Com corte menor, uma cidade pequena cortada pela
rodovia contaria como explorada mesmo passando direto.

**A marca é do pedal, não da cidade** — o pedal é exploração se atravessou ao
menos uma cidade inédita. Em agosto de 2026 saí de Ipaumirim rumo a Triunfo:
Ipaumirim e Baixio eu já conhecia, Triunfo e Umari não, então o pedal é
exploração. O do dia seguinte, só em Ipaumirim e Baixio, é rotina.

**Casos de borda resolvidos**

- *Pedais sem coordenada* (5): são todos rotina urbana, estrada, e o porte sai
  da distância. O padrão já acerta.
- *Primeira vez de Fortaleza* (junho de 2021): marca exploração. É o marco
  inicial do histórico, fica assim.
- *Dois pedais no mesmo dia* (12/08/2025): passaram por lugares diferentes, sem
  conflito.

**Limitação conhecida** — A malha do IBGE só tem municípios. Olho d'Água é
distrito de Ipaumirim, então um pedal até lá aparece como se eu tivesse ficado
em Ipaumirim. Exploração de distrito não é detectável com este dado.
