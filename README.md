# 🍯 HoneyChain — Autonomous Hive Telemetry & Web3 Honey Provenance Ledger

HoneyChain is an anti-fraud decentralized supply chain, hive telemetry, and honey provenance platform. It establishes cryptographic proof of origin and quality for every harvested jar by cross-referencing real-time IoT hive sensor drops against reported yields, accredited IPFS laboratory certificates, and tamper-evident smart contracts.

---

## 1. Overview & Core Philosophy

### The Zero-Crypto Principle
Producers, beekeepers, and consumers **never manage private keys, gas fees, or crypto wallets**. 
The backend operates as an authenticated **Trusted Web3 Relayer**, submitting gasless signed transactions on behalf of authorized actors using Role-Based Access Control (RBAC).

```
[IoT Sensors / MQTT] ──┐
                       ├──> [Backend API Gateway] ──> [SQLite / PostgreSQL / IPFS]
[Beekeeper/Lab/Agent] ──┘             │
                                      ▼
                           [Web3 Relayer Service] ──> [HoneyChain Smart Contract (EVM)]
```

### Core Anti-Fraud Guardrails
1. **IoT Yield Anomaly Cross-Checking**: Reported harvest weights are strictly checked against physical IoT hive weight-drop curves (`verify_yield_integrity()` via Isolation Forest). Discrepancies $> 2.5\text{ kg}$ trigger automatic audit alerts.
2. **Dual Attestation**: Harvest batch creation requires designated consent from both the collection `Agent` and the registered `Beekeeper` (with cryptographic ECDSA signature verification).
3. **Automated Batch Downgrade Rule**: If a tamper-evident seal is broken in transit prior to official packaging (`SealStatus.Broken`), the smart contract **must automatically downgrade** `BatchType` from `SingleOrigin` to `CooperativeBlended`.
4. **Two-Stage Consumer Verification**:
   - **Public QR Scan**: Read-only public query returning origin village, brix score, and IPFS lab certificate.
   - **Hidden Scratch-Off Code**: Plaintext scratch code revealed by consumer is hashed with `keccak256` to claim physical possession and prevent counterfeit duplicates.
5. **Data Division Guardrail**: Precise GPS coordinates and personally identifiable information (PII) are strictly stored off-chain. Only privacy-preserving fuzzed village clusters and cryptographic hashes are committed to the public blockchain ledger.

---

## 2. File Tree Architecture

```
plan-bee/
├── .agents/                               # Agent configuration and active development skills
│   └── skills/
│       ├── blockchain-developer/         # Smart contract state machine & relayer architecture
│       │   ├── SKILL.md                   # Core Web3 & smart contract developer guidelines
│       │   └── blockchain.md              # HoneyChain technical specification & anti-fraud matrix
│       ├── mastering-typescript/          # Enterprise TypeScript typing and safety patterns
│       ├── migrate-radix-to-base/         # Radix to Base UI migration & component patterns
│       │   ├── universal-patterns.md      # Layouts, render prop model, Portal > Backdrop > Popup
│       │   └── disclosure.md              # Modals, Dialogs, Tabs, and Toggle primitives
│       ├── playwright-best-practices/     # End-to-end and browser testing standards
│       ├── premium-frontend-ui/           # Immersive UI craftsmanship & performance motion rules
│       ├── shadcn/                        # shadcn/ui design tokens and component composition
│       └── typescript-unit-testing/       # Unit testing best practices and AAA patterns
│
├── blockchain/                            # Hardhat 3 EVM workspace
│   ├── contracts/
│   │   ├── HoneyChain.sol                 # Primary smart contract (AccessControl, RBAC, state machine)
│   │   ├── Counter.sol                    # Starter contract template
│   │   └── Counter.t.sol                  # Foundry-compatible Solidity unit test
│   ├── ignition/modules/
│   │   ├── HoneyChain.ts                  # Hardhat Ignition deployment module for HoneyChain
│   │   └── Counter.ts                     # Ignition deployment module for Counter
│   ├── scripts/
│   │   ├── deploy.ts                      # Standalone deployment script configuring relayer roles
│   │   └── send-op-tx.ts                  # Optimism L2 transaction simulation script
│   ├── test/
│   │   ├── HoneyChain.ts                  # Comprehensive TypeScript Mocha test suite (17/17 passing)
│   │   └── Counter.ts                     # Mocha unit tests for Counter
│   ├── hardhat.config.ts                  # Hardhat 3 configuration (solc 0.8.34, viaIR, localhost)
│   └── package.json                       # Dependencies (@openzeppelin/contracts, ethers, hardhat)
│
├── backend/                               # Python FastAPI Relayer & API Gateway
│   ├── anomaly_service.py                 # Isolation Forest & rule-based yield integrity validator
│   ├── blockchain_bridge.py               # Web3.py non-custodial transaction relayer bridge
│   ├── main.py                            # FastAPI gateway implementing REST endpoints & SQLite DB
│   ├── test_e2e.py                        # Automated end-to-end integration test suite
│   ├── simulator.py                       # IoT sensor telemetry generator
│   ├── requirements.txt                   # Backend Python dependencies (fastapi, web3, scikit-learn)
│   └── .env                               # Relayer wallet, RPC URL, and contract configuration
│
├── frontend/                              # Vite + React + TypeScript Dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                        # Base UI & shadcn primitives
│   │   │   │   ├── badge.tsx              # Semantic status badges
│   │   │   │   ├── button.tsx             # Button with render prop and honey variants
│   │   │   │   ├── card.tsx               # Full card composition system
│   │   │   │   ├── dialog.tsx             # Base UI Backdrop + Popup modal dialog
│   │   │   │   └── tabs.tsx               # Base UI Tabs component
│   │   │   ├── Navbar.tsx                 # Sticky navigation with node & relayer status
│   │   │   ├── MetricsOverview.tsx        # High-level KPIs (hives, batches, brix, anomaly rate)
│   │   │   ├── TelemetryDataGrid.tsx      # Real-time hive telemetry data grid (universal-patterns)
│   │   │   ├── BatchProvenanceViewer.tsx  # Provenance state pipeline & scratch-claim portal
│   │   │   └── WalletSignatureModal.tsx   # Base UI dual-attestation ECDSA signature modal
│   │   ├── lib/utils.ts                   # Tailwind class merge utility (cn)
│   │   ├── App.tsx                        # Main dashboard application
│   │   ├── main.tsx                       # React DOM root entrypoint
│   │   └── index.css                      # Tailwind theme variables, amber glow, and Base UI hooks
│   ├── index.html                         # HTML template with typography imports
│   ├── vite.config.ts                     # Vite build configuration and backend API proxy
│   ├── tailwind.config.js                 # Honey color palette and design system configuration
│   └── package.json                       # Frontend dependencies (@base-ui/react, lucide-react)
│
├── app/                                   # Microservice starter entrypoint
│   └── main.py                            # Lightweight FastAPI healthcheck endpoint
│
├── docker-compose.yml                     # Local services (PostgreSQL 15, Eclipse Mosquitto MQTT)
├── skills-lock.json                       # Cryptographic hash lockfile for active skills
└── README.md                              # Definitive project documentation
```

---

## 3. Tech Stack & Engineering Mechanics

### Smart Contract & Blockchain Layer
- **Language**: Solidity `^0.8.20` (compiled with `solc 0.8.34`, EVM target: Osaka).
- **Tooling**: **Hardhat 3** (`hardhat@^3.15.0`), **Hardhat Ignition** (`@nomicfoundation/hardhat-ignition`), **Ethers.js v6**.
- **Security & Libraries**:
  - OpenZeppelin Contracts v5 (`@openzeppelin/contracts@^5.2.0`):
    - `AccessControl`: Granular role enforcement (`DEFAULT_ADMIN_ROLE`, `AGENT_ROLE`, `LAB_ROLE`, `BEEKEEPER_ROLE`, `RETAILER_ROLE`).
    - `ECDSA` & `MessageHashUtils`: Dual-attestation cryptographic signature recovery (`createHarvestBatchWithSignature`).
- **Compiler Optimization**: `viaIR: true`, Optimizer enabled (`runs: 200`) preventing stack-too-deep on complex supply chain structs.

### Backend Relayer & API Gateway
- **Framework**: **FastAPI** (`fastapi>=0.115.0`), **Uvicorn**, **Pydantic v2**.
- **Blockchain Connectivity**: **Web3.py v8** (`web3>=7.0.0`) with server-side transaction signing (`send_relayed_transaction`).
- **Machine Learning & Anomaly Detection**:
  - `scikit-learn` (`IsolationForest` anomaly scoring).
  - `numpy` (array processing of weight drop curves).
- **Databases**:
  - SQLite (`honeychain.db`) with dynamic schema migration.
  - PostgreSQL 15 & Eclipse Mosquitto (configured via `docker-compose.yml`).
  - IPFS Pinata Gateway integration for accredited PDF lab reports.

### Frontend Dashboard
- **Framework**: **React 18** + **Vite 5** + **TypeScript 5**.
- **Styling**: **Tailwind CSS v3** with custom amber honey color scales (`#f59e0b`, `#fbbf24`), frosted glassmorphism overlays (`backdrop-blur-xl`), and dark obsidian palettes (`#070709`).
- **UI Primitives**:
  - **Base UI** (`@base-ui/react`): Modern unstyled primitives adhering to the `render` prop paradigm (avoiding `asChild`), `Backdrop` + `Popup` modal composition.
  - **shadcn/ui**: Semantic design tokens, `Card` composition, `Badge` statuses, and `FieldGroup` input patterns.
  - **Icons**: `lucide-react`.

### Testing Layers
| Layer | Framework / Tools | Coverage |
|---|---|---|
| **Smart Contract Tests** | Hardhat 3, Mocha, Chai, Ethers v6 | 17/17 passing tests verifying roles, seal downgrades, dual attestation, and scratch claims. |
| **End-to-End Integration** | `backend/test_e2e.py`, FastAPI TestClient | 7-step test verifying health, IoT drop curves, relayer execution, lab reports, consumer claims, and seal breaks. |
| **Frontend Production Build** | TypeScript (`tsc`) + Vite | Strict type safety, clean bundle output (`dist/`) with zero warnings. |

---

## 4. Active Agent Skills & Development Criteria

Incoming AI agents and developers must strictly follow the local guidelines defined in `.agents/skills/`:

### 1. `blockchain-developer` & `blockchain.md`
- **Zero-Crypto Overhead**: Producers, beekeepers, and consumers never manage private keys or gas; all transactions route through the authenticated backend relayer.
- **Data Division Guardrail**: Never record precise latitude/longitude or user personally identifiable information (PII) on the blockchain ledger.
- **Strict Role Modifiers**: Enforce `onlyRole` access control modifiers on state-changing contract functions.
- **Anti-Fraud State Machine**: Always enforce pre-packaging seal-break checks and the automatic downgrade rule (`SingleOrigin` $\to$ `CooperativeBlended`).

### 2. `premium-frontend-ui`
- **Visual Identity**: Maintain the cyber-organic aesthetic with warm amber glows, frosted glassmorphism, and high typographic contrast.
- **Performance Imperative**: Animate only hardware-accelerated properties (`transform` and `opacity`); fiercely avoid animating layout properties (`width`, `height`, `margin`, `top`).
- **Accessibility**: Include `@media (prefers-reduced-motion: no-preference)` safeguards.

### 3. `shadcn`
- **Composition Over Reinvention**: Compose interfaces using `Card`, `Badge`, `Button`, `Dialog`, and `Tabs`.
- **Semantic Color Tokens**: Use semantic classes (`bg-primary`, `text-muted-foreground`, `border-border`) rather than hardcoded colors.
- **Form Architecture**: Use `FieldGroup` + `Field` + `FieldLabel` rather than unstructured `div` elements.

### 4. `migrate-radix-to-base` (`universal-patterns.md` & `disclosure.md`)
- **`render` Prop Paradigm**: Base UI uses the `render` prop instead of Radix's `asChild` (e.g. `<DialogClose render={<Button />}>`).
- **Portal / Positioning Architecture**: Modals compose as `Portal > Backdrop + Popup` (centered modals do not use an outer positioner).
- **Presence Data Attributes**: Use presence attributes (`data-open`, `data-closed`, `data-starting-style`, `data-ending-style`) for CSS transition hooks.

---

## 5. Quick Start & Execution Guide

### 1. Run Smart Contract Tests
```bash
cd blockchain
npm install
npx hardhat test
```

### 2. Start Local Blockchain & Deploy Contract
```bash
# Terminal 1: Start Hardhat EVM Node (Port 8545)
cd blockchain
npx hardhat node

# Terminal 2: Deploy Contract and Grant Relayer Roles
cd blockchain
npx hardhat run scripts/deploy.ts --network localhost
```

### 3. Start Backend Relayer API Gateway (Port 8000)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Run Automated E2E Suite**: `python test_e2e.py`

### 4. Start Frontend Dashboard (Port 5173)
```bash
cd frontend
npm install
npm run dev
```
- **Live Web3 Dashboard**: [http://localhost:5173](http://localhost:5173)

