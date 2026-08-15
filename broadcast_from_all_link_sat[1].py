
import asyncio
import websockets
import json
import requests
import time

# CONFIG - TON ALL LINK SAT
WSS_ALL_LINK_SAT = "wss://all-link.fxion.local:443"
WS_LOCAL = "ws://0.0.0.0:8765"
MEMPOOL_API = "https://mempool.space/api/tx"

WALLETS = [
    "bc1qhfqw4amua8g04lfww5utaanne737tfumjmy7te",
    "bc1qgh8ccarsurqd833prj5xmdj2kt5yzujj7vf2xn"
]

async def fetch_and_broadcast():
    print(f"Connecting to ALL LINK SAT: {WSS_ALL_LINK_SAT}")
    print(f"Local: {WS_LOCAL}")
    
    try:
        async with websockets.connect(WSS_ALL_LINK_SAT) as ws_sat:
            print("Connected to all-link.sat")
            
            # Demande tout le mesh complet avec raw
            await ws_sat.send(json.dumps({
                "op": "get_all_mesh",
                "include_raw": True,
                "filter": "isMy=true",
                "wallets": WALLETS
            }))
            
            all_txs = []
            while True:
                try:
                    msg = await asyncio.wait_for(ws_sat.recv(), timeout=10)
                    data = json.loads(msg)
                    
                    if data.get('type') == 'tx' or 'txid' in data:
                        all_txs.append(data)
                        txid = data.get('txid','')[:16]
                        raw = data.get('raw','') or data.get('hex','')
                        status = data.get('status','')
                        print(f"[{len(all_txs)}] {txid}... status={status} raw_len={len(raw)}")
                        
                        # Si raw présent, broadcast direct vers mempool
                        if raw and len(raw) > 100:
                            try:
                                resp = requests.post(MEMPOOL_API, data=raw, headers={"Content-Type":"text/plain"}, timeout=10)
                                if resp.status_code == 200:
                                    print(f"  -> BROADCASTED to mempool: {resp.text[:80]}")
                                elif "already" in resp.text.lower() or "exists" in resp.text.lower():
                                    print(f"  -> Already in mempool: VERIFIED")
                                else:
                                    print(f"  -> Mempool response {resp.status_code}: {resp.text[:100]}")
                            except Exception as e:
                                print(f"  -> Broadcast error: {e}")
                            time.sleep(0.5)
                    
                    elif data.get('type') == 'done' or data.get('op') == 'complete':
                        print(f"\nAll mesh fetched: {len(all_txs)} tx")
                        break
                        
                except asyncio.TimeoutError:
                    print("Timeout - fetching done")
                    break
            
            print(f"\nTotal fetched from all-link.sat: {len(all_txs)}")
            return all_txs
            
    except Exception as e:
        print(f"WSS failed {e}, trying WS local {WS_LOCAL}")
        try:
            async with websockets.connect(WS_LOCAL) as ws_local:
                await ws_local.send(json.dumps({"op":"get_all","include_raw":True}))
                all_txs = []
                while True:
                    try:
                        msg = await asyncio.wait_for(ws_local.recv(), timeout=5)
                        data = json.loads(msg)
                        if 'txid' in data:
                            all_txs.append(data)
                            raw = data.get('raw','')
                            if raw:
                                requests.post(MEMPOOL_API, data=raw, headers={"Content-Type":"text/plain"})
                                print(f"Broadcasted {data.get('txid','')[:16]}")
                    except asyncio.TimeoutError:
                        break
                return all_txs
        except Exception as e2:
            print(f"Both WSS failed: {e2}")
            return []

# Version synchrone simple si websockets pas dispo
def fetch_via_http():
    print("Trying HTTP fallback for all-link.sat...")
    endpoints = [
        "http://0.0.0.0:8765/api/tx?include_raw=1&isMy=true",
        "https://all-link.fxion.local:443/api/tx?include_raw=1",
        "http://0.0.0.0:8765/dump?full=1&include_raw=1"
    ]
    for url in endpoints:
        try:
            print(f"Trying {url}")
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                txs = data.get('txRows', data) if isinstance(data, dict) else data
                print(f"Got {len(txs)} tx from {url}")
                for tx in txs:
                    raw = tx.get('raw') or tx.get('hex')
                    if raw and tx.get('isMy'):
                        try:
                            resp = requests.post(MEMPOOL_API, data=raw, headers={"Content-Type":"text/plain"})
                            print(f"{tx.get('txid','')[:16]} -> {resp.status_code} {resp.text[:60]}")
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"Error {e}")
                return txs
        except Exception as e:
            print(f"Failed {url}: {e}")
    return []

if __name__ == "__main__":
    try:
        # Essaye async WSS
        asyncio.run(fetch_and_broadcast())
    except:
        # Fallback HTTP
        fetch_via_http()
