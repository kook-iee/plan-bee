import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

class BlockchainBridge:
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None,
        artifact_path: Optional[str] = None,
    ):
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "http://127.0.0.1:8545")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        # Default fallback test key (Hardhat standard test account #0) if not set
        default_dev_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        self.private_key = private_key or os.getenv("BACKEND_WALLET_PRIVATE_KEY", default_dev_key)

        try:
            self.relayer_account = self.w3.eth.account.from_key(self.private_key)
        except Exception:
            self.relayer_account = None

        env_contract_addr = contract_address or os.getenv("CONTRACT_ADDRESS")
        if env_contract_addr and Web3.is_address(env_contract_addr):
            self.contract_address = Web3.to_checksum_address(env_contract_addr)
        else:
            self.contract_address = None

        self.abi = self._load_abi(artifact_path)
        self.contract = None
        if self.contract_address and self.abi:
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

    def _load_abi(self, artifact_path: Optional[str] = None) -> list:
        search_paths = [
            artifact_path,
            os.getenv("CONTRACT_ARTIFACT_PATH"),
            str(Path(__file__).parent.parent / "blockchain" / "artifacts" / "contracts" / "HoneyChain.sol" / "HoneyChain.json"),
            str(Path(__file__).parent / "HoneyChain.json"),
        ]
        for p in search_paths:
            if p and os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("abi", data)
                except Exception:
                    continue
        return []

    def set_contract_address(self, address: str):
        self.contract_address = Web3.to_checksum_address(address)
        if self.abi:
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

    def is_connected(self) -> bool:
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def compute_scratch_code_hash(self, raw_scratch_code: str) -> bytes:
        """Computes keccak256 hash matching on-chain claimConsumer lookup."""
        return self.w3.keccak(text=raw_scratch_code)

    def send_relayed_transaction(self, func_call, gas_limit: int = 400000) -> str:
        """Signs and broadcasts a transaction from the backend relayer account."""
        if not self.relayer_account:
            raise RuntimeError("Backend relayer account is not configured.")
        if not self.is_connected():
            raise ConnectionError(f"Cannot connect to blockchain RPC at {self.rpc_url}")

        nonce = self.w3.eth.get_transaction_count(self.relayer_account.address)
        gas_price = self.w3.eth.gas_price

        tx = func_call.build_transaction({
            "from": self.relayer_account.address,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": gas_price,
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.relayer_account.key)
        raw_tx = getattr(signed_tx, "raw_transaction", getattr(signed_tx, "rawTransaction", None))
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        return self.w3.to_hex(tx_hash)

    def create_harvest_batch(
        self,
        batch_id: int,
        village: str,
        weight_grams: int,
        beekeeper_address: str,
        scratch_code_hash: bytes,
        beekeeper_signature: Optional[bytes] = None,
    ) -> str:
        if not self.contract:
            raise RuntimeError("HoneyChain contract is not loaded or address is missing.")

        checksum_beekeeper = Web3.to_checksum_address(beekeeper_address)

        if beekeeper_signature:
            func = self.contract.functions.createHarvestBatchWithSignature(
                batch_id,
                village,
                weight_grams,
                checksum_beekeeper,
                scratch_code_hash,
                beekeeper_signature
            )
        else:
            func = self.contract.functions.createHarvestBatch(
                batch_id,
                village,
                weight_grams,
                checksum_beekeeper,
                scratch_code_hash
            )

        return self.send_relayed_transaction(func)

    def log_seal_break(self, batch_id: int) -> str:
        if not self.contract:
            raise RuntimeError("HoneyChain contract is not loaded.")
        func = self.contract.functions.logSealBreak(batch_id)
        return self.send_relayed_transaction(func)

    def attach_lab_report(self, batch_id: int, ipfs_hash: str, brix: int) -> str:
        if not self.contract:
            raise RuntimeError("HoneyChain contract is not loaded.")
        func = self.contract.functions.attachLabReport(batch_id, ipfs_hash, brix)
        return self.send_relayed_transaction(func)

    def package_batch(self, batch_id: int) -> str:
        if not self.contract:
            raise RuntimeError("HoneyChain contract is not loaded.")
        func = self.contract.functions.packageBatch(batch_id)
        return self.send_relayed_transaction(func)

    def release_batch(self, batch_id: int, retailer_address: str) -> str:
        if not self.contract:
            raise RuntimeError("HoneyChain contract is not loaded.")
        checksum_retailer = Web3.to_checksum_address(retailer_address)
        func = self.contract.functions.releaseBatch(batch_id, checksum_retailer)
        return self.send_relayed_transaction(func)

    def claim_consumer(self, raw_scratch_code: str) -> str:
        if not self.contract:
            raise RuntimeError("HoneyChain contract is not loaded.")
        func = self.contract.functions.claimConsumer(raw_scratch_code)
        return self.send_relayed_transaction(func)

    def get_batch_public(self, batch_id: int) -> Dict[str, Any]:
        """Executes read-only call to fetch public batch metadata."""
        if not self.contract:
            raise RuntimeError("HoneyChain contract is not loaded.")

        state_names = ["Harvested", "Tested", "Sealed", "Packaged", "Released", "Claimed"]
        type_names = ["SingleOrigin", "CooperativeBlended"]
        seal_names = ["Intact", "Broken"]

        data = self.contract.functions.getBatchPublic(batch_id).call()
        # [batchId, village, harvestTimestamp, weightGrams, brixRating, labReportIPFSHash, state, batchType, sealStatus, beekeeper, collectionAgent, isClaimed]
        return {
            "batch_id": data[0],
            "origin_village": data[1],
            "harvest_timestamp": data[2],
            "weight_grams": data[3],
            "brix_rating": data[4] / 10.0 if data[4] > 100 else float(data[4]),
            "lab_report_ipfs_hash": data[5],
            "lab_report_url": f"https://ipfs.io/ipfs/{data[5]}" if data[5] else None,
            "state": state_names[data[6]] if data[6] < len(state_names) else str(data[6]),
            "batch_type": type_names[data[7]] if data[7] < len(type_names) else str(data[7]),
            "seal_status": seal_names[data[8]] if data[8] < len(seal_names) else str(data[8]),
            "beekeeper": data[9],
            "collection_agent": data[10],
            "is_claimed": data[11],
        }

bridge = BlockchainBridge()

