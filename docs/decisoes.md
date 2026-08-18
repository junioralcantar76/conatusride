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

## 19. Classificação — aplicada, mas a rever

**Estado** — Os três campos da decisão 15 foram implementados em
`src/classificar.py` e rodam sobre a base:

| Campo | Valores |
|---|---|
| `tipo` | rotina, treino, evento, viagem |
| `porte` | curto, medio, longo |
| `exploracao` | sim, não |

**Região de rotina** — sete municípios: Fortaleza, Caucaia, Maracanaú,
Maranguape, Aquiraz, Eusébio, Pindoretama. Não é a Região Metropolitana legal:
Paracuru, Paraipaba, Trairi, São Luís do Curu, Chorozinho, Pacajus, Horizonte,
Guaiúba, Itaitinga, Pacatuba e Cascavel foram retirados, porque ir até lá não é
rotina vivida.

Basta uma das pontas do pedal estar na região para ser rotina — quem sai de
Fortaleza rumo a Chorozinho, ou volta de Beberibe para casa, fez pedal de rotina.

**Viagem x evento** — fora da região, dias de pedal agrupados com tolerância de
até 3 dias de folga formam viagem; dia isolado é evento. A tolerância de 3 dias
existe porque em férias há descanso no meio, e um corte rígido jogava pedais
soltos para evento.

**Resultado** — 13 eventos detectados, todos corretos (11 com "Trilha" no nome,
mais Guaramiranga e Apuiarés). Exploração: 3 em 2021, 10 em 2022, depois 5 a 6
por ano.

**A rever** — Foram acrescentados campos e regras além do que estava combinado
(`dentro_regiao`, `cidade_nova`, o CSV de eventos, a discussão de piso). Antes
de seguir, definir juntos quais campos ficam.

---

## 20. Trilha — definida, não aplicada

**Definição do ciclista** — pedal cuja maior parte da rota não é asfalto:
estrada de terra, calçamento ou singletrack. Pode atravessar cidade no caminho.

**Como identificar** — pelo nome. O termo "trilha" é sempre usado no nome do
pedal no Strava, e isso continuará.

**Exceção conhecida** — "Aventura: Cofeco, trilha do mangue, Mangabeira"
(18/09/2022) tem "trilha" no nome mas é pedal de rotina de domingo, 70 km, com
um trecho curto de trilha. Uma exceção em cinco anos.

**O dado do Strava não serve** — a coluna `distancia_terra_m` marca 1% na Trilha
Apuiarés, que foi quase toda em terra. As estradas dessas regiões não constam
como não pavimentadas no mapa do Strava. Não usar nem como complemento.

**Onde entra** — num campo `piso` com três valores: estrada, trilha, misto.
Separado de `tipo`. Falta definir o critério de misto.

---

## 21. O CSV de eventos foi descartado

**Decisão** — `docs/eventos.csv` e `src/eventos.py` não entram no projeto.

**Razão** — Foram propostos para cobrir eventos dentro da região de rotina, que
a regra automática não detecta. Na prática, misturaram trilha e evento numa
lista só e criaram mais confusão do que resolveram. A classificação automática
funciona sem eles.
