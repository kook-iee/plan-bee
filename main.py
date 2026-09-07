import hashlib
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from web3 import Web3

from anomaly_service import verify_yield_integrity
from blockchain_bridge import bridge

app = FastAPI(title="Honey Chain Backend & Web3 Relayer API", version="1.0.0")
DB_FILE = os.getenv("DB_FILE", "honeychain.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY,
            numeric_id INTEGER UNIQUE,
            beekeeper_id TEXT,
            beekeeper_wallet TEXT,
            hive_id TEXT,
            location TEXT,
            fuzzed_village TEXT,
            floral_source TEXT,
            reported_weight_grams INTEGER,
            brix_field_reading REAL,
            scratch_code_hash TEXT,
            blockchain_tx_hash TEXT,
            seal_status TEXT DEFAULT 'Intact',
            state TEXT DEFAULT 'Harvested',
            batch_type TEXT DEFAULT 'SingleOrigin',
            is_claimed INTEGER DEFAULT 0,
            claimed_at TEXT,
            created_at INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT,
            hive_id TEXT,
            weight_kg REAL,
            temperature_c REAL,
            humidity_pct REAL,
            timestamp INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT,
            brix_rating REAL,
            ipfs_cid TEXT,
            tx_hash TEXT,
            created_at INTEGER
        )
    ''')
    conn.commit()

    # Dynamic migrations for pre-existing SQLite databases
    cursor.execute("PRAGMA table_info(telemetry)")
    telemetry_cols = [c[1] for c in cursor.fetchall()]
    if "hive_id" not in telemetry_cols:
        cursor.execute("ALTER TABLE telemetry ADD COLUMN hive_id TEXT")

    cursor.execute("PRAGMA table_info(batches)")
    batches_cols = [c[1] for c in cursor.fetchall()]
    migrations = [
        ("numeric_id", "INTEGER"),
        ("beekeeper_wallet", "TEXT"),
        ("hive_id", "TEXT"),
        ("fuzzed_village", "TEXT"),
        ("reported_weight_grams", "INTEGER"),
        ("brix_field_reading", "REAL"),
        ("scratch_code_hash", "TEXT"),
        ("blockchain_tx_hash", "TEXT"),
        ("seal_status", "TEXT DEFAULT 'Intact'"),
        ("state", "TEXT DEFAULT 'Harvested'"),
        ("batch_type", "TEXT DEFAULT 'SingleOrigin'"),
        ("is_claimed", "INTEGER DEFAULT 0"),
        ("claimed_at", "TEXT")
    ]
    for col, col_type in migrations:
        if col not in batches_cols:
            try:
                cursor.execute(f"ALTER TABLE batches ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    conn.commit()
    conn.close()

init_db()

# --- Pydantic Request Models ---

class BatchCreate(BaseModel):
    batch_id: str
    beekeeper_id: str
    location: str
    floral_source: str

class TelemetryLog(BaseModel):
    batch_id: str
    hive_id: Optional[str] = None
    weight_kg: float
    temperature_c: float
    humidity_pct: float

class HarvestLogRequest(BaseModel):
    batch_id: Optional[int] = None
    hive_id: str
    beekeeper_id: str
    beekeeper_wallet: Optional[str] = None
    reported_weight_grams: int
    brix_field_reading: float
    raw_scratch_code: str
    fuzzed_village: Optional[str] = "Rampur Cluster, District Shimla"

class SealBreakRequest(BaseModel):
    batch_id: int

# --- API Endpoints ---

@app.get("/api/v1/health")
def health_check():
    connected = bridge.is_connected()
    return {
        "status": "healthy",
        "blockchain_connected": connected,
        "contract_loaded": bridge.contract is not None,
        "contract_address": bridge.contract_address,
        "relayer_address": bridge.relayer_account.address if bridge.relayer_account else None
    }

@app.post("/api/v1/harvest/log", status_code=status.HTTP_201_CREATED)
def log_harvest(payload: HarvestLogRequest):
    """
    AGENT role endpoint to log honey harvest:
    1. Cross-checks telemetry history for yield anomalies.
    2. Hashes scratch code using keccak256.
    3. Relays on-chain createHarvestBatch transaction.
    4. Records state in off-chain database.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Determine numeric batch ID
    if payload.batch_id:
        numeric_id = payload.batch_id
    else:
        cursor.execute("SELECT MAX(numeric_id) FROM batches")
        row = cursor.fetchone()
        numeric_id = (row[0] or 1000) + 1

    batch_str_id = f"BATCH-{numeric_id}"

    # Verify Yield Integrity via Anomaly Service
    cursor.execute(
        "SELECT weight_kg FROM telemetry WHERE batch_id = ? OR hive_id = ? ORDER BY timestamp ASC",
        (batch_str_id, payload.hive_id)
    )
    rows = cursor.fetchall()
    sensor_history = [{"weight": r[0]} for r in rows]
    reported_kg = payload.reported_weight_grams / 1000.0
    yield_verification = verify_yield_integrity(sensor_history, reported_kg)

    # Compute keccak256 scratch code hash
    scratch_hash_bytes = bridge.compute_scratch_code_hash(payload.raw_scratch_code)
    scratch_hash_hex = "0x" + scratch_hash_bytes.hex()

    # Determine beekeeper address
    default_beekeeper = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Hardhat account #1
    beekeeper_addr = payload.beekeeper_wallet or default_beekeeper

    # Relayed Blockchain Transaction
    tx_hash = None
    if bridge.is_connected() and bridge.contract:
        try:
            tx_hash = bridge.create_harvest_batch(
                batch_id=numeric_id,
                village=payload.fuzzed_village,
                weight_grams=payload.reported_weight_grams,
                beekeeper_address=beekeeper_addr,
                scratch_code_hash=scratch_hash_bytes
            )
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")
    else:
        tx_hash = "mock_tx_" + hashlib.sha256(f"{numeric_id}_{time.time()}".encode()).hexdigest()[:16]

    # Save to database
    try:
        cursor.execute(
            '''
            INSERT INTO batches (
                batch_id, numeric_id, beekeeper_id, beekeeper_wallet, hive_id,
                location, fuzzed_village, reported_weight_grams, brix_field_reading,
                scratch_code_hash, blockchain_tx_hash, seal_status, state, batch_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Intact', 'Harvested', 'SingleOrigin', ?)
            ''',
            (
                batch_str_id, numeric_id, payload.beekeeper_id, beekeeper_addr, payload.hive_id,
                payload.fuzzed_village, payload.fuzzed_village, payload.reported_weight_grams,
                payload.brix_field_reading, scratch_hash_hex, tx_hash, int(time.time())
            )
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Batch ID {numeric_id} already exists: {str(e)}")
    finally:
        conn.close()

    return {
        "status": "created",
        "batch_id": numeric_id,
        "batch_code": batch_str_id,
        "tx_hash": tx_hash,
        "scratch_code_hash": scratch_hash_hex,
        "yield_integrity": yield_verification
    }

@app.post("/api/v1/lab/attach-report")
async def attach_lab_report(
    batch_id: int = Form(...),
    brix_rating: float = Form(...),
    ipfs_cid: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None)
):
    """
    LAB role endpoint to attach certified laboratory report:
    1. Uploads PDF or utilizes provided IPFS CID.
    2. Relays attachLabReport smart contract call.
    """
    cid = ipfs_cid
    if not cid:
        if pdf_file:
            content = await pdf_file.read()
            # Deterministic CID representation for test/local
            cid = "Qm" + hashlib.sha256(content).hexdigest()[:44]
        else:
            cid = "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"

    # Scaled integer for Solidity (e.g., 81.5% -> 815)
    brix_scaled = int(brix_rating * 10) if brix_rating < 100 else int(brix_rating)

    tx_hash = None
    if bridge.is_connected() and bridge.contract:
        try:
            tx_hash = bridge.attach_lab_report(batch_id, cid, brix_scaled)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to attach report on-chain: {str(e)}")
    else:
        tx_hash = "mock_lab_tx_" + hashlib.sha256(f"{batch_id}_{cid}".encode()).hexdigest()[:16]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO lab_reports (batch_id, brix_rating, ipfs_cid, tx_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(batch_id), brix_rating, cid, tx_hash, int(time.time()))
    )
    cursor.execute(
        "UPDATE batches SET state = 'Tested' WHERE numeric_id = ? OR batch_id = ?",
        (batch_id, f"BATCH-{batch_id}")
    )
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "batch_id": batch_id,
        "ipfs_cid": cid,
        "blockchain_tx": tx_hash,
        "lab_report_url": f"https://ipfs.io/ipfs/{cid}"
    }

@app.post("/api/v1/batch/seal-break")
def log_seal_break(payload: SealBreakRequest):
    """
    AGENT role endpoint: logs seal break and forces CooperativeBlended downgrade on-chain.
    """
    tx_hash = None
    if bridge.is_connected() and bridge.contract:
        try:
            tx_hash = bridge.log_seal_break(payload.batch_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"On-chain seal break log failed: {str(e)}")
    else:
        tx_hash = "mock_seal_tx_" + hashlib.sha256(f"{payload.batch_id}".encode()).hexdigest()[:16]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE batches SET seal_status = 'Broken', batch_type = 'CooperativeBlended' WHERE numeric_id = ? OR batch_id = ?",
        (payload.batch_id, f"BATCH-{payload.batch_id}")
    )
    conn.commit()
    conn.close()

    return {
        "status": "seal_break_logged",
        "batch_id": payload.batch_id,
        "new_seal_status": "Broken",
        "new_batch_type": "CooperativeBlended",
        "tx_hash": tx_hash
    }

@app.get("/api/v1/verify/{scratch_code}")
def verify_and_claim_consumer(scratch_code: str):
    """
    Public (Unauthenticated) consumer verification & claim endpoint:
    1. Computes keccak256(scratch_code).
    2. Submits claimConsumer transaction on-chain.
    3. Returns on-chain provenance and IPFS lab certificate link.
    """
    scratch_hash = bridge.compute_scratch_code_hash(scratch_code)
    scratch_hash_hex = "0x" + scratch_hash.hex()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batches WHERE scratch_code_hash = ?", (scratch_hash_hex,))
    row = cursor.fetchone()

    on_chain_data = None
    first_claim = True
    batch_num = row["numeric_id"] if row else None

    if bridge.is_connected() and bridge.contract:
        try:
            bridge.claim_consumer(scratch_code)
            first_claim = True
        except Exception as e:
            # If already claimed, on-chain revert message is "Code already claimed"
            if "already claimed" in str(e).lower():
                first_claim = False
            else:
                pass

        if batch_num:
            try:
                on_chain_data = bridge.get_batch_public(batch_num)
            except Exception:
                pass

    now_iso = datetime.now(timezone.utc).isoformat()
    if row and first_claim and row["is_claimed"] == 0:
        cursor.execute(
            "UPDATE batches SET is_claimed = 1, state = 'Claimed', claimed_at = ? WHERE scratch_code_hash = ?",
            (now_iso, scratch_hash_hex)
        )
        conn.commit()
    elif row and row["is_claimed"] == 1:
        first_claim = False
        now_iso = row["claimed_at"] or now_iso

    conn.close()

    if not row and not on_chain_data:
        raise HTTPException(status_code=404, detail="Invalid scratch code.")

    # Lab report lookup
    lab_cid = None
    if on_chain_data and on_chain_data.get("lab_report_ipfs_hash"):
        lab_cid = on_chain_data["lab_report_ipfs_hash"]
    else:
        lab_cid = "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"

    return {
        "batch_id": batch_num or (on_chain_data["batch_id"] if on_chain_data else None),
        "batch_type": on_chain_data["batch_type"] if on_chain_data else (row["batch_type"] if row else "SingleOrigin"),
        "seal_status": on_chain_data["seal_status"] if on_chain_data else (row["seal_status"] if row else "Intact"),
        "origin_village": on_chain_data["origin_village"] if on_chain_data else (row["fuzzed_village"] if row else "Rampur Cluster, District Shimla"),
        "lab_report_url": f"https://ipfs.io/ipfs/{lab_cid}",
        "is_first_claim": first_claim,
        "claimed_at": now_iso
    }

@app.get("/api/v1/batch/{batch_id}/public")
def get_public_batch(batch_id: int):
    """
    Public Read-Only QR Scan:
    Returns safe provenance without revealing scratch code hash.
    """
    if bridge.is_connected() and bridge.contract:
        try:
            return bridge.get_batch_public(batch_id)
        except Exception:
            pass

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batches WHERE numeric_id = ? OR batch_id = ?", (batch_id, f"BATCH-{batch_id}"))
    batch = cursor.fetchone()
    conn.close()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    return {
        "batch_id": batch["numeric_id"],
        "origin_village": batch["fuzzed_village"],
        "reported_weight_grams": batch["reported_weight_grams"],
        "brix_rating": batch["brix_field_reading"],
        "seal_status": batch["seal_status"],
        "batch_type": batch["batch_type"],
        "state": batch["state"],
        "is_claimed": bool(batch["is_claimed"])
    }

# --- Legacy Endpoints for Telemetry & Simulator Compatibility ---

@app.post("/api/batches")
def create_batch_legacy(batch: BatchCreate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO batches (batch_id, beekeeper_id, location, floral_source, created_at) VALUES (?, ?, ?, ?, ?)",
            (batch.batch_id, batch.beekeeper_id, batch.location, batch.floral_source, int(time.time()))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Batch ID already exists.")
    conn.close()
    return {"status": "success", "batch_id": batch.batch_id}

@app.post("/api/telemetry")
def log_telemetry_legacy(data: TelemetryLog):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO telemetry (batch_id, hive_id, weight_kg, temperature_c, humidity_pct, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (data.batch_id, data.hive_id, data.weight_kg, data.temperature_c, data.humidity_pct, int(time.time()))
    )
    conn.commit()
    conn.close()
    return {"status": "success", "batch_id": data.batch_id}

@app.get("/api/batches/{batch_id}")
def get_batch_legacy(batch_id: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,))
    batch = cursor.fetchone()
    if not batch:
        conn.close()
        raise HTTPException(status_code=404, detail="Batch not found")

    cursor.execute("SELECT weight_kg, temperature_c, humidity_pct, timestamp FROM telemetry WHERE batch_id = ? ORDER BY timestamp DESC", (batch_id,))
    telemetry = [dict(row) for row in cursor.fetchall()]
    conn.close()

    result = dict(batch)
    result["telemetry_logs"] = telemetry
    return result
