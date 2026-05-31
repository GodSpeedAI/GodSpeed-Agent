const os = require("os");
const path = require("path");

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function embedText(text, dimensions = 128) {
  const vector = new Array(dimensions).fill(0);
  const tokens = String(text || "")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);

  for (const token of tokens) {
    let hash = 2166136261;
    for (let index = 0; index < token.length; index += 1) {
      hash ^= token.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    const slot = Math.abs(hash) % dimensions;
    vector[slot] += 1;
  }

  const magnitude = Math.sqrt(vector.reduce((total, value) => total + value * value, 0));
  if (magnitude === 0) {
    return vector;
  }
  return vector.map((value) => value / magnitude);
}

function loadVectorDb() {
  const ruvector = require("ruvector");
  const candidate = ruvector.VectorDB || (ruvector.default && ruvector.default.VectorDB);
  if (!candidate) {
    throw new Error("RuVector VectorDB export is unavailable");
  }
  return candidate;
}

async function main() {
  const raw = await readStdin();
  const payload = JSON.parse(raw || "{}");
  const documents = Array.isArray(payload.documents) ? payload.documents : [];
  const query = String(payload.query || "");
  const limit = Number(payload.limit || 5);

  const VectorDB = loadVectorDb();
  const db = new VectorDB({
    dimensions: 128,
    storagePath: path.join(os.tmpdir(), `godspeed-ruvector-${process.pid}-${Date.now()}.db`),
  });
  const byId = new Map();

  for (const document of documents) {
    const recordId = String(document.record_id || "");
    if (!recordId) {
      continue;
    }
    const vector = embedText(document.text || "", 128);
    await db.insert({ id: recordId, vector, metadata: document.metadata || {} });
    byId.set(recordId, document);
  }

  const queryVector = embedText(query, 128);
  const rawResults = (await db.search({ vector: queryVector, k: limit })) || [];
  const results = rawResults
    .map((item) => {
      const id = String(item.id || item.key || "");
      const document = byId.get(id);
      if (!document) {
        return null;
      }
      return {
        record_id: id,
        ledger: document.ledger,
        score: Number(item.score || item.similarity || item.distance || 0),
        metadata: item.metadata || document.metadata || {},
        text: document.text,
      };
    })
    .filter(Boolean);

  process.stdout.write(
    JSON.stringify({
      provider: "ruvector",
      query,
      result_count: results.length,
      results,
    }),
  );
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exit(1);
});