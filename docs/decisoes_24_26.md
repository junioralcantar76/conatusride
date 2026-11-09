## 24. Histórico com filtros combináveis

**Decisão** — `historico.html` lista todos os pedais com filtros de ano, mês,
piso, porte, tipo, busca por nome e distância mínima. Abre no ano corrente.

**Por que não em "todos os anos"** — 974 linhas de uma vez não é ponto de
partida útil. O ano corrente já é um recorte que se lê, e o resto está a um
clique.

**Rota ao clique** — as cidades atravessadas aparecem só quando a linha é
aberta. Mostrá-las sempre dobraria a altura da tabela. Custa ~30 KB a mais no
JSON embutido, o que é irrelevante.

**Ordenação** — pelos cabeçalhos de data, km, tempo, ritmo e subida.

---

## 25. Comparação entre anos

**Decisão** — `anos.html` traz a tabela com os anos lado a lado (total, pedais,
média por pedal, meses com registro, variação sobre o ano anterior) e o gráfico
mês a mês com uma cor por ano. Seletor de medida: km, pedais, elevação, horas.

**Recorte "até o mês atual"** — caixa que corta todos os anos no mesmo ponto.
Sem ela, o ano corrente aparece sempre muito abaixo só porque não acabou. Vem
desmarcada, e o mês é calculado a partir do último pedal registrado — fixar
"setembro" quebraria o rótulo na virada do mês.

**A medida muda a leitura** — por km, 2026 parece pequeno; por elevação, tem a
maior média por pedal de todos os anos.

---

## 26. Mapa em SVG, sem biblioteca nem camada de imagem

**Decisão** — `mapa.html` desenha os contornos do IBGE direto em SVG, a partir
de `data/contornos.json`.

**Razão** — Uma biblioteca de mapa puxaria imagens de fundo da internet, e as
páginas deixariam de funcionar offline. O traço simples também combina melhor
com o resto do painel.

**Três níveis** — Brasil com os 27 estados e os visitados destacados; ao clicar
num estado, os municípios daquele estado, mais escuros onde passei mais vezes;
ao clicar numa cidade, quantos pedais e desde quando.

**Projeção** — a longitude é achatada pelo cosseno da latitude média, senão o
Brasil sai esticado no sentido leste-oeste. Mercator seria exagero para a faixa
de latitude de um país só.

**Contornos** — `src/contornos.py` extrai da malha do IBGE via geobr, simplifica
e grava em `data/contornos.json`. Só os municípios dos estados onde pedalei
(574 dos 5.570); o Brasil municipal inteiro seria pesado demais.

**Tolerância** — 0.08 grau para estados, 0.03 para municípios, coordenadas com
3 casas (~110 m). Resultado: 28,5 mil pontos e 506 KB, contra 62 mil e 1,2 MB
com os valores iniciais. Mais simplificação deixa os contornos angulosos.

**O arquivo fica fora do Git**, como o resto de `data/`: é derivado, e quem
clonar o repositório roda o script e o reproduz.

**O mapa só é gerado se o arquivo existir** — sem ele, o `gerar_site.py` avisa e
segue, e a aba aparece apagada no menu.
