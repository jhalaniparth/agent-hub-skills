## MCP transport swap

For MCP servers only (A2A agents skip this section).

Replace `stdio_server` with a Starlette app using `StreamableHTTPSessionManager`:

```python
import os
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

app = Server('my-mcp-server')
# ... register @app.list_tools() and @app.call_tool() unchanged ...

session_manager = StreamableHTTPSessionManager(
    app=app, event_store=None, json_response=False, stateless=True
)

async def health(request):
    return JSONResponse({'status': 'ok'})

starlette_app = Starlette(
    routes=[
        Route('/health', health),
        Route('/mcp', endpoint=StreamableHTTPASGIApp(session_manager)),
    ],
    lifespan=lambda _: session_manager.run(),
)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    uvicorn.run(starlette_app, host='0.0.0.0', port=port)
```

Use `/health` as the health check endpoint in `manifest.yml`.
Add to `requirements.txt`: `starlette`, `uvicorn[standard]`, `sse-starlette`, `httpx-sse`.
`stateless=True` is required for multi-instance CF scaling.
