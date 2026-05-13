import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const PORT = process.env.PORT || 3000;
const HOST = '127.0.0.1';

const ROOT = fileURLToPath(new URL('.', import.meta.url));
const DESKTOP_DIR = join(ROOT, 'desktop');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif':  'image/gif',
  '.ico':  'image/x-icon',
  '.txt':  'text/plain; charset=utf-8',
};

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

/**
 * 静的ファイルを desktop/ から安全に返す
 * pathname: "/desktop/style.css" のような形式
 */
async function serveStatic(res, pathname) {
  // "/desktop/" を取り除いて相対パスにする
  const rel = pathname.replace(/^\/desktop\/?/, '');
  const abs = normalize(join(DESKTOP_DIR, rel));

  // ディレクトリトラバーサル防御：DESKTOP_DIR の外を指していないか
  if (!abs.startsWith(DESKTOP_DIR + sep) && abs !== DESKTOP_DIR) {
    return json(res, 403, { error: 'Forbidden' });
  }

  const target = abs === DESKTOP_DIR ? join(DESKTOP_DIR, 'index.html') : abs;

  try {
    const data = await readFile(target);
    const type = MIME[extname(target).toLowerCase()] || 'application/octet-stream';
    res.writeHead(200, {
      'Content-Type': type,
      'Content-Length': data.length,
      'Cache-Control': 'no-cache',
    });
    res.end(data);
  } catch (err) {
    if (err.code === 'ENOENT' || err.code === 'EISDIR') {
      return json(res, 404, { error: 'Not Found' });
    }
    throw err;
  }
}

/** ルーティング */
async function handleRequest(req, res) {
  const { method, url } = req;

  // GET / → デスクトップUI
  if (method === 'GET' && (url === '/' || url === '/index.html')) {
    return serveStatic(res, '/desktop/index.html');
  }

  // GET /desktop/* → 静的ファイル
  if (method === 'GET' && url.startsWith('/desktop')) {
    return serveStatic(res, url.split('?')[0]);
  }

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
