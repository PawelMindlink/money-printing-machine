# Money Printing Machine 🖨️💸

**Automated Marketing Intelligence System**

## Definition

**Business Goal**: Automatically allocate advertising budget to high-potential e-commerce products by classifying them into strategic tiers (P1-P8) based on cross-channel performance (GA4 + Meta Ads + Feed).

**Audience**: Marketing Engineers, Data Analysts, n8n Developers.

## Operation

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Execution

You can run the pipeline locally or deploy the API.

**Local Simulation**:

```bash
# Run verifying simulation with local data
python tests/reproduce_n8n_priority.py
```

**Live API**:
The system is deployed on Render.
POST `https://money-printing-machine.onrender.com/process` with JSON payload.

### 3. Workflow

1. **Data Ingestion**: n8n fetches data (GA4, Feed, Meta).
2. **Processing**: n8n sends payload to this Python API (`src/main.py`).
3. **Classification**: API returns priority tiers.
4. **Action**: n8n updates ad sets based on tiers.

## Structure

- **`src/`**: Core application logic.
  - `main.py`: API Entry point (FastAPI).
  - `business_logic_layer.py`: URL matching and margin logic.
- **`tests/`**: Verification scripts.
  - `reproduce_n8n_priority.py`: Local logic simulation.
  - `test_api_live.py`: Live endpoint verification.
- **`scripts/`**: Operational tools.
  - `debug/`: One-off investigation scripts.
  - `ops/`: Monitoring and bridge scripts.
- **`Input/`**: Local test data (GitIgnored, confidential).
- **`Workflows/`**: n8n JSON exports.

## n8n Integration

Ten projekt wykorzystuje **n8n Atom** do synchronizacji workflowów między tym repozytorium a Twoją instancją n8n.

1. **Workflows**: Wszystkie workflowy znajdują się w folderze `Workflows/`.
2. **Synchronizacja**:
    - Zainstaluj rozszerzenie [n8n Atom](https://www.atom8n.com/) w swoim edytorze.
    - Podłącz folder `Workflows/` do swojej instancji n8n.
    - Każda zmiana w pliku `.n8n` zostanie automatycznie odzwierciedlona w n8n.

### Pierwszy Import

Jeśli nie używasz jeszcze n8n Atom, możesz ręcznie zaimportować plik:
`Workflows/Daily_Report_Workflow.n8n` -> **Import from File** w UI n8n.
