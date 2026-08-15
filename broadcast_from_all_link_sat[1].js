
// BROADCAST FROM ALL-LINK.SAT - Node.js version for Bell 638
const WebSocket = require('ws');
const https = require('https');

const WSS = "wss://all-link.fxion.local:443";
const WS_LOCAL = "ws://0.0.0.0:8765";
const MEMPOOL_API = "https://mempool.space/api/tx";

const wallets = [
  "bc1qhfqw4amua8g04lfww5utaanne737tfumjmy7te",
  "bc1qgh8ccarsurqd833prj5xmdj2kt5yzujj7vf2xn"
];

function broadcastToMempool(rawHex, txid) {
  return new Promise((resolve) => {
    const req = https.request(MEMPOOL_API, {
      method: 'POST',
      headers: {'Content-Type':'text/plain'}
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        console.log(`[${txid.slice(0,16)}] mempool ${res.statusCode}: ${data.slice(0,80)}`);
        resolve();
      });
    });
    req.on('error', e => { console.log(`Error ${txid}: ${e.message}`); resolve(); });
    req.write(rawHex);
    req.end();
  });
}

async function run() {
  console.log(`Connecting to ${WSS}`);
  const ws = new WebSocket(WSS);
  
  ws.on('open', () => {
    console.log('Connected to all-link.sat');
    ws.send(JSON.stringify({op:"get_all_mesh", include_raw:true, filter:"isMy=true", wallets}));
  });
  
  let count = 0;
  ws.on('message', async (msg) => {
    try {
      const data = JSON.parse(msg);
      if (data.txid && data.raw) {
        count++;
        console.log(`[${count}] ${data.txid.slice(0,16)} status=${data.status} value=${data.valueBtc} raw=${data.raw.length}`);
        if (data.isMy) {
          await broadcastToMempool(data.raw, data.txid);
          await new Promise(r => setTimeout(r, 500));
        }
      }
      if (data.type === 'done') {
        console.log(`Done - ${count} tx broadcasted`);
        ws.close();
      }
    } catch(e) { console.log('Parse error', e.message); }
  });
  
  ws.on('error', (e) => {
    console.log(`WSS error ${e.message}, trying ${WS_LOCAL}`);
    // fallback to local
    const ws2 = new WebSocket(WS_LOCAL);
    ws2.on('open', () => ws2.send(JSON.stringify({op:"get_all", include_raw:true})));
    ws2.on('message', async (msg) => {
      const data = JSON.parse(msg);
      if (data.raw && data.isMy) {
        await broadcastToMempool(data.raw, data.txid);
      }
    });
  });
}

run();
