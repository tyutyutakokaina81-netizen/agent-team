import { createServer } from 'node:http';

const PORT = process.env.PORT || 3000;
const HOST = '127.0.0.1';

const MAX_BODY_BYTES = 1024 * 1024; // 1MB

/** JSON レスポンスを返すヘルパー */
function json(res, status, body) {
  if (res.headersSent) return; // 送信済みなら二重レスポンスを試みない
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

/** リクエストボディを読み取る（上限超過は 413 用のエラー） */
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > MAX_BODY_BYTES) {
        req.destroy();
        const err = new Error('Payload Too Large');
        err.statusCode = 413;
        reject(err);
        return;
      }
      chunks.push(c);
    });
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
    let body;
    try {
      body = await readBody(req);
    } catch (err) {
      return json(res, err.statusCode === 413 ? 413 : 500,
        { error: err.statusCode === 413 ? 'Payload Too Large' : 'Internal Server Error' });
    }
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
