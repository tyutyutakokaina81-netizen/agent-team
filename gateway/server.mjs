import { createServer } from 'node:http';

const PORT = process.env.PORT || 3000;
const HOST = '127.0.0.1';

/** JSON レスポンスを返すヘルパー */
function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

/** リクエストボディを読み取る */
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString()));
    req.on('error', reject);
  });
}

/** ルーティング */
async function handleRequest(req, res) {
  const { method, url } = req;

  // GET /health
  if (method === 'GET' && url === '/health') {
    return json(res, 200, { ok: true, time: new Date().toISOString() });
  }

  // GET /version
  if (method === 'GET' && url === '/version') {
    return json(res, 200, { name: 'agent-gateway', version: '0.1.0' });
  }

  // POST /echo
  if (method === 'POST' && url === '/echo') {
    const body = await readBody(req);
    let parsed;
    try {
      parsed = JSON.parse(body);
    } catch {
      return json(res, 400, { error: 'Invalid JSON' });
    }
    return json(res, 200, parsed);
  }

  // 404
  json(res, 404, { error: 'Not Found' });
}

const server = createServer(async (req, res) => {
  const start = performance.now();
  try {
    await handleRequest(req, res);
  } catch (err) {
    json(res, 500, { error: 'Internal Server Error' });
  }
  const ms = (performance.now() - start).toFixed(2);
  console.log(`${req.method} ${req.url} ${res.statusCode} ${ms}ms`);
});

server.listen(PORT, HOST, () => {
  console.log(`Listening on http://${HOST}:${PORT}`);
});
