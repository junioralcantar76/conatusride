## 27. v2 — atualização incremental pela API

**Decisão** — `src/atualizar.py` busca na API do Strava os pedais posteriores ao
último da base, baixa o traçado de cada um e grava nas mesmas tabelas. A
exportação continua sendo o caminho da carga inicial e da recuperação do zero.

**Razão** — A exportação refaz 974 arquivos para acrescentar 5. Só o
`tracos.py` leva 15 minutos reprocessando o que não mudou. Pela API são
segundos.

**OAuth** — Aplicativo registrado em `strava.com/settings/api`, escopo
`activity:read_all`, callback em `localhost`. A autorização é feita uma vez no
navegador; o script que trocou o código pelos tokens foi apagado depois, porque
tinha o Client Secret escrito dentro e `src/` vai para o Git.

**Tokens** — Ficam em `data/strava_token.json`, fora do Git. O access token dura
6 horas e é renovado na hora do uso, com 60 s de folga; o refresh token não
expira.

**Campos que a API não traz** — clima, inclinação e distância em terra. Pedais
vindos por aqui ficam com esses campos nulos. Não quebra nada: o piso é marcado
pelo nome (decisão 21) e o clima nunca foi usado em análise.

**Traçado** — Os fluxos `latlng` e `time`, amostrados por minuto como o
`tracos.py` faz com os arquivos. Amostrar pelo tempo real, e não contando
pontos, vale porque a taxa de gravação varia entre aparelhos.

**A regra de elevação implausível** (decisão 23) vale aqui também, com o mesmo
corte de 30 m/km.

---

## 28. A atualização é idempotente

**Decisão** — Antes de inserir, o script descarta as atividades cujo id já está
na base. E a busca recua um dia do último pedal, em vez de partir dele exato.

**Razão** — O parâmetro `after` da API compara pela data em UTC, e a base guarda
a hora local — três horas de diferença. O último pedal da base voltava na busca,
e rodar duas vezes seguidas quebrava com erro de chave duplicada.

Filtrar por id resolve de vez: o script pode rodar quantas vezes quiser, e a
folga de um dia ainda cobre atividades editadas depois de gravadas.

**Lição** — Um script de atualização tem de poder ser rodado de novo sem
consequência. Se roda duas vezes e quebra, é defeito do script.

---

## 29. Atalho `atualizar.bat`

**Decisão** — Um `.bat` na raiz ativa o ambiente, roda os três scripts
(`atualizar`, `classificar`, `gerar_site`) e abre o painel. Para na primeira
falha em vez de seguir adiante.

**Armadilha** — Arquivo `.bat` exige quebra de linha CRLF e codificação
Windows-1252. Salvo em LF, o interpretador lê tudo como uma linha e cospe
centenas de erros. Vale conferir no VS Code, no canto inferior direito.

---

## 30. `src/consulta.py` fora do Git

**Decisão** — O rascunho de consultas entrou no `.gitignore` e saiu do
rastreamento com `git rm --cached`.

**Razão** — Ele muda a cada uso, polui o histórico e é onde credenciais acabam
coladas por engano durante um teste.
