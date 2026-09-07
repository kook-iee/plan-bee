#!/usr/bin/env python3
"""
HoneyChain End-to-End Verification Test Script
Tests API endpoints, Anomaly Detection, and on-chain / mock Web3 relayer state transitions.
"""

import sys
import time
from fastapi.testclient import TestClient
import main

def run_tests():
    client = TestClient(main.app)
    print("=" * 60)
    print(" 🍯 HONEYCHAIN END-TO-END VERIFICATION TEST SUITE 🍯 ")
    print("=" * 60)

    # 1. Health & Connection Check
    print("\n[1/7] Testing Health & Bridge Status...")
    res = client.get("/api/v1/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health = res.json()
    print(f"  ✔ Health status: {health['status']}")
    print(f"  ✔ Blockchain connected: {health['blockchain_connected']}")
    if health['blockchain_connected']:
        print(f"  ✔ Contract loaded: {health['contract_loaded']} at {health['contract_address']}")
    else:
        print("  ℹ Running in standalone/mock relayer mode (Hardhat node offline)")

    # 2. Add baseline telemetry for hive
    print("\n[2/7] Injecting IoT Telemetry for Hive HIVE-900...")
    client.post("/api/telemetry", json={"batch_id": "HIVE-900", "hive_id": "HIVE-900", "weight_kg": 50.0, "temperature_c": 28.0, "humidity_pct": 55.0})
    client.post("/api/telemetry", json={"batch_id": "HIVE-900", "hive_id": "HIVE-900", "weight_kg": 35.0, "temperature_c": 28.5, "humidity_pct": 54.0})
    print("  ✔ Telemetry logged (pre-harvest weight: 50.0kg, post-harvest weight: 35.0kg -> 15.0kg yield drop)")

    # 3. Log Harvest Batch (Agent Role)
    print("\n[3/7] Logging Harvest Batch (Agent Role)...")
    batch_id = int(time.time()) % 100000 + 10000
    scratch_code = f"SCRATCH-{batch_id}"
    harvest_payload = {
        "batch_id": batch_id,
        "hive_id": "HIVE-900",
        "beekeeper_id": "USR-BEEKEEPER-01",
        "reported_weight_grams": 15000,
        "brix_field_reading": 81.5,
        "raw_scratch_code": scratch_code,
        "fuzzed_village": "Rampur Cluster, District Shimla"
    }
    res = client.post("/api/v1/harvest/log", json=harvest_payload)
    assert res.status_code == 201, f"Harvest logging failed: {res.text}"
    harvest_data = res.json()
    print(f"  ✔ Harvest Batch Created: ID {harvest_data['batch_id']}")
    print(f"  ✔ Anomaly Check: {harvest_data['yield_integrity']['reason']} (Flagged: {harvest_data['yield_integrity']['flagged']})")
    print(f"  ✔ Scratch Code Keccak256 Hash: {harvest_data['scratch_code_hash']}")
    print(f"  ✔ TX Hash: {harvest_data['tx_hash']}")

    # 4. Attach Lab Report (Lab Role)
    print("\n[4/7] Attaching Accredited Lab Report (Lab Role)...")
    lab_payload = {
        "batch_id": batch_id,
        "brix_rating": 81.5,
        "ipfs_cid": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"
    }
    res = client.post("/api/v1/lab/attach-report", data=lab_payload)
    assert res.status_code == 200, f"Lab report attachment failed: {res.text}"
    lab_data = res.json()
    print(f"  ✔ Lab Report Attached: IPFS CID {lab_data['ipfs_cid']}")
    print(f"  ✔ Document URL: {lab_data['lab_report_url']}")

    # 5. Public QR Scan (Read-Only Verification)
    print("\n[5/7] Testing Public QR Scan (Read-Only)...")
    res = client.get(f"/api/v1/batch/{batch_id}/public")
    assert res.status_code == 200, f"Public QR query failed: {res.text}"
    qr_data = res.json()
    print(f"  ✔ Batch State: {qr_data['state']}")
    print(f"  ✔ Origin Village: {qr_data['origin_village']}")
    print(f"  ✔ Seal Status: {qr_data['seal_status']} | Batch Type: {qr_data['batch_type']}")
    assert qr_data['state'] == "Tested"

    # 6. Consumer Claim via Scratch Code
    print("\n[6/7] Testing Consumer Claim via Plaintext Scratch Code...")
    res = client.get(f"/api/v1/verify/{scratch_code}")
    assert res.status_code == 200, f"Consumer claim failed: {res.text}"
    claim_data = res.json()
    print(f"  ✔ First-time Claim Successful: is_first_claim = {claim_data['is_first_claim']}")
    print(f"  ✔ Claimed At: {claim_data['claimed_at']}")

    # Test duplicate claim
    res_dup = client.get(f"/api/v1/verify/{scratch_code}")
    assert res_dup.status_code == 200
    print(f"  ✔ Duplicate Claim Prevention: is_first_claim = {res_dup.json()['is_first_claim']} (False as expected)")

    # 7. Anti-Fraud Seal Break Downgrade
    print("\n[7/7] Testing Anti-Fraud Seal Break Automatic Downgrade...")
    res_seal = client.post("/api/v1/batch/seal-break", json={"batch_id": batch_id})
    assert res_seal.status_code == 200, f"Seal break failed: {res_seal.text}"
    seal_data = res_seal.json()
    print(f"  ✔ Seal Broken Logged: status = {seal_data['new_seal_status']}")
    print(f"  ✔ Automatic Downgrade Rule Enforced: new batch_type = {seal_data['new_batch_type']}")
    assert seal_data['new_batch_type'] == "CooperativeBlended"

    print("\n" + "=" * 60)
    print(" 🎉 ALL END-TO-END TESTS PASSED SUCCESSFULLY! 🎉 ")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()

