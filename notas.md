# notas.md — Notas do desenvolvedor

## Arquitetura

O projeto usa FastAPI com lifespan para gerenciar o worker de background
que consome a fila de scraping. O motor (engine.py) usa um semaforo para
limitar a 5 conexoes simultaneas.

## Fila com prioridade

Usei asyncio.PriorityQueue que ordena tuplas (prioridade, timestamp).
Prioridade ALTA = 0, NORMAL = 1, BAIXA = 2. Tarefas de mesma prioridade
seguem FIFO gracas ao timestamp_criacao no dataclass.

## Proxy rotation

O proxy pool testa cada proxy contra httpbin.org/ip com timeout curto (5s).
Se nenhum proxy funciona, o scraping segue sem proxy. Na engine, a cada
tentativa de retry a gente troca de proxy.

## Retry com backoff

Quando aiohttp da erro (timeout, conexao fechada, 5xx), a engine faz
backoff exponencial: 1s, 2s, 4s... e tenta novamente com outro proxy e
outro user-agent.

## Variaveis em pt-br

Usei nomes como url_alvo, seletor_css, tentativas e tempo_restante
nos parametros das funcoes e nos campos dos dataclasses, como pedido.

## Pontos de melhoria

- Adicionar autenticacao basica na API
- Suporte a JavaScript (Playwright) para SPAs
- Cache de resultados em Redis
- WebSocket para notificacoes em tempo real
- Rate limiting por dominio
- Exportar CSV com aiofiles ao inves de csv sincrono
