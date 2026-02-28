# async-scraper-api

**Async web scraping API** built with FastAPI, aiohttp, and BeautifulSoup.
Queue-based task processing with priority levels, proxy rotation, and user-agent rotation.

## Features

- ⚡ **Async scraping** — non-blocking I/O via `aiohttp`, max 5 simultaneous connections
- 📋 **Task queue** — priority-based queue (`alta`, `normal`, `baixa`) with `asyncio.PriorityQueue`
- 🔄 **Proxy rotation** — configurable proxy pool with connectivity testing
- 🎭 **User-agent rotation** — random UA selection from a built-in pool
- ⏱ **Configurable timeout** — per-task timeout with exponential backoff retry (3 attempts)
- 📊 **Result export** — JSON and CSV export, saved to `results/` directory
- 🖥 **Web dashboard** — Bootstrap 5 dark UI for task management
- 🔌 **REST API** — `/api/scrape`, `/api/tasks`, `/api/results`, `/api/stats`

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py

# Open in browser
# http://localhost:8000/dashboard
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/scrape` | Create a new scraping task |
| GET | `/api/tasks` | List all tasks (optional `?status=` filter) |
| GET | `/api/tasks/{id}` | Get task details |
| GET | `/api/results` | List all saved results |
| GET | `/api/results/{id}` | Get result JSON |
| GET | `/api/stats` | Engine statistics |
| GET | `/dashboard` | Web dashboard |
| GET | `/tasks/{id}` | Task detail page |

### POST /api/scrape

```json
{
    "url_alvo": "https://example.com",
    "seletor_css": "h1.title",
    "prioridade": "normal",
    "timeout": 30,
    "max_tentativas": 3
}
```

## Configuration

Edit `config.py` or use environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Debug mode / auto-reload |
| `MAX_CONEXOES` | `5` | Max simultaneous HTTP connections |
| `TIMEOUT_PADRAO` | `30` | Default request timeout (seconds) |
| `MAX_TENTATIVAS` | `3` | Max retry attempts |
| `BACKOFF_BASE` | `1.0` | Exponential backoff base (seconds) |
| `PROXY_TIMEOUT` | `5` | Proxy connectivity test timeout |

## Project Structure

```
async-scraper-api/
├── main.py              # FastAPI entry point
├── config.py            # Settings & configuration
├── scraper/
│   ├── engine.py        # Async scraping engine
│   ├── parser.py        # HTML parsers (generic + custom)
│   ├── proxy.py         # Proxy pool with rotation
│   ├── ua_rotation.py   # User-agent pool
│   ├── queue.py         # Priority task queue
│   └── results.py       # Result export (JSON/CSV)
├── web/
│   ├── routes.py        # REST API + dashboard routes
│   ├── templates/       # Jinja2 templates (Bootstrap 5 dark)
│   └── static/          # Static assets (CSS)
├── samples/             # Example configurations
├── results/             # Saved scraping results
├── requirements.txt
└── README.md
```

## License

MIT
