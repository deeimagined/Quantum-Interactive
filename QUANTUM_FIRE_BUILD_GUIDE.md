# QUANTUM-FIRE — Complete Build Guide
## GitHub + TouchDesigner + Frontend Handoff

---

# PART 1: ADD FILES TO GITHUB
*(Do this first so your collaborator can start the Streamlit frontend)*

### Step 1 — Add quantum_art_pipeline.py to your repo

```bash
# In Terminal, navigate to your cloned repo
cd ~/path/to/Quantum-Interactive

# Copy the pipeline file in (or just move it)
cp ~/Desktop/quantum_art_pipeline.py .

# Stage, commit, push
git add quantum_art_pipeline.py
git commit -m "Add quantum art pipeline — fires IBM job, saves quantum_data.json"
git push origin main
```

### Step 2 — Add a README so your collaborator knows the data contract

Create `README.md` in the repo root with this content:

```markdown
# QUANTUM-FIRE

## Data Flow
quantum_art_pipeline.py → ~/Desktop/quantum_data.json → TouchDesigner / Streamlit

## quantum_data.json Structure
| Field | Type | Used by |
|-------|------|---------|
| metadata.timestamp | string | Streamlit display |
| metadata.backend | string | Streamlit display |
| metadata.shots | int | Both |
| measurement_counts | dict[state→int] | Streamlit histogram |
| probabilities | dict[state→float] | TouchDesigner fire |
| qubit_bias | dict[qubit→float] | TouchDesigner per-qubit layers |
| entropy.shannon_entropy | float (0–∞) | TouchDesigner turbulence |
| entropy.normalized_entropy | float (0–1) | TouchDesigner brightness |
| sample_bitstrings | list[str] | Streamlit live feed |

## Setup
1. Set IBM_QUANTUM_TOKEN env variable
2. Run: python quantum_art_pipeline.py
3. Output saved to ~/Desktop/quantum_data.json
4. TouchDesigner auto-reloads via File In DAT
```

### Step 3 — Also push the TouchDesigner builder
```bash
git add quantum_fire_td_builder.py
git commit -m "Add TouchDesigner network builder script"
git push origin main
```

---

# PART 2: TOUCHDESIGNER — MANUAL NODE BUILD
*(Do this if you prefer building by hand and seeing each connection)*

## Setup: Before You Start
- Open TouchDesigner (free version works)
- File → New project
- Press `P` to open the Network Editor
- Right-click to create nodes, or press `Tab` to search

---

## SECTION A: Data Layer (DATs)

### Node 1 — File In DAT
1. Right-click in network → DAT → **File In**
2. In Parameters panel (press `P` with node selected):
   - `File` → `/Users/YOURUSERNAME/Desktop/quantum_data.json`
   - `Sync to File` → **ON** ← critical, this auto-reloads on change
3. Rename it: double-click name → type `qfire_filein`

### Node 2, 3, 4 — Table DATs
Create 3 Table DATs. Rename them:
- `qfire_table_probs`
- `qfire_table_qubits`
- `qfire_table_meta`

*(Leave them empty — the parser script fills them)*

### Node 5 — Text DAT (holds parser code)
1. Create → DAT → **Text DAT**, rename `qfire_parser_text`
2. Double-click to open editor
3. Paste this code:

```python
import json

def cook(scriptDAT):
    file_dat = op("qfire_filein")
    data = json.loads(file_dat.text)

    probs   = data["probabilities"]
    qubits  = data["qubit_bias"]
    entropy = data["entropy"]
    meta    = data["metadata"]

    # Probabilities table
    t = op("qfire_table_probs")
    t.clear()
    t.appendRow(["state", "probability"])
    for state, prob in probs.items():
        t.appendRow([state, prob])

    # Qubit bias table
    t2 = op("qfire_table_qubits")
    t2.clear()
    t2.appendRow(["qubit", "bias"])
    for qubit, bias in qubits.items():
        t2.appendRow([qubit, bias])

    # Entropy + meta table
    t3 = op("qfire_table_meta")
    t3.clear()
    t3.appendRow(["key", "value"])
    t3.appendRow(["shannon_entropy",    entropy["shannon_entropy"]])
    t3.appendRow(["normalized_entropy", entropy["normalized_entropy"]])
    t3.appendRow(["shots",              meta["shots"]])
    t3.appendRow(["unique_states",      meta["unique_states"]])
```

### Node 6 — Script DAT (runs the parser)
1. Create → DAT → **Script DAT**, rename `qfire_parser`
2. Parameters:
   - `DAT` → `qfire_parser_text`
3. Right-click `qfire_filein` → Outputs → connect wire to `qfire_parser`
   *(This makes the parser re-run whenever the file changes)*

**Test it:** Right-click `qfire_parser` → **Run Script**
Check that `qfire_table_probs` now has 10 rows (header + 9 states)

---

## SECTION B: CHOP Layer (data → numbers)

### Node 7 — DAT to CHOP (probabilities)
1. Create → CHOP → **DAT to**, rename `qfire_dat2chop_probs`
2. Parameters:
   - `DAT` → `qfire_table_probs`
   - `Select Rows` → `By Index`
   - `Start Row Index` → `1` (skip header)
   - `Select Cols` → `By Name`
   - `Col Names` → `probability`
3. You should see 9 channels, one per quantum state

### Node 8 — Normalize CHOP
1. Create → CHOP → **Normalize**, rename `qfire_normalize`
2. Connect `qfire_dat2chop_probs` → `qfire_normalize`
3. Parameters:
   - `Range` → `0 to 1`

### Node 9 — Trail CHOP (smooths transitions between jobs)
1. Create → CHOP → **Trail**, rename `qfire_trail`
2. Connect `qfire_normalize` → `qfire_trail`
3. Parameters:
   - `Window Unit` → `Seconds`
   - `Window Length` → `0.5`

### Node 10 — DAT to CHOP (qubit bias)
1. Create → CHOP → **DAT to**, rename `qfire_dat2chop_qubits`
2. Parameters:
   - `DAT` → `qfire_table_qubits`
   - `Start Row Index` → `1`
   - `Col Names` → `bias`
3. You'll see 5 channels: qubit_0 through qubit_4

### Node 11 — DAT to CHOP (entropy/meta)
1. Create → CHOP → **DAT to**, rename `qfire_dat2chop_meta`
2. Parameters:
   - `DAT` → `qfire_table_meta`
   - `Start Row Index` → `1`
   - `Col Names` → `value`

---

## SECTION C: Visual Layer (TOPs)

### Node 12 — Noise TOP (fire base)
1. Create → TOP → **Noise**, rename `qfire_noise`
2. Parameters:
   - `Type` → `Sparse`
   - `Translate Y` → right-click → **Add Expression** → type: `absTime.seconds * 0.3`
   - `Amplitude` → right-click → **Add Expression** → type: `op('qfire_normalize')['chan1']`
   - `Roughness` → right-click → **Add Expression** → type: `op('qfire_dat2chop_meta')['chan1']`
     *(chan1 = shannon_entropy row = 0.8414 in your data)*

### Node 13 — Feedback TOP (fire trails)
1. Create → TOP → **Feedback**, rename `qfire_feedback`
2. Connect `qfire_noise` → `qfire_feedback`
3. Parameters:
   - `TOP` → `qfire_feedback` *(points back to itself — creates the loop)*
   - `Opacity` → `0.85`

### Node 14 — Blur TOP
1. Create → TOP → **Blur**, rename `qfire_blur`
2. Connect `qfire_feedback` → `qfire_blur`
3. Parameters:
   - `Filter` → `Gaussian`
   - `Size X` → `8`
   - `Size Y` → `8`

### Node 15 — Level TOP
1. Create → TOP → **Level**, rename `qfire_level`
2. Connect `qfire_blur` → `qfire_level`
3. Parameters:
   - `Brightness` → `1.2`
   - `Contrast` → `1.4`

### Node 16 — Ramp TOP (fire color palette)
1. Create → TOP → **Ramp**, rename `qfire_ramp`
2. Parameters → `Type` → `Linear` (horizontal)
3. Click the color bar to edit gradient:
   - Stop 1 (pos 0.0): Black `#000000`
   - Stop 2 (pos 0.4): Deep red `#990000`
   - Stop 3 (pos 0.7): Orange `#FF6600`
   - Stop 4 (pos 1.0): Hot white `#FFF5E0`

### Node 17 — Lookup TOP (apply fire colors)
1. Create → TOP → **Lookup**, rename `qfire_lookup`
2. Connect:
   - Input 1 (top-left): `qfire_level`
   - Input 2 (bottom-left): `qfire_ramp`
3. This maps grayscale fire intensity → fire color

### Node 18 — Out TOP
1. Create → TOP → **Out**, rename `qfire_out`
2. Connect `qfire_lookup` → `qfire_out`

---

## SECTION D: Test It

1. Make sure `quantum_data.json` exists on your Desktop
2. Right-click `qfire_parser` → **Run Script**
3. Click `qfire_out` — you should see fire
4. Now run `python quantum_art_pipeline.py` in Terminal
5. Watch the fire reshape as new quantum data lands

---

# PART 3: PROGRAMMATIC BUILD
*(Alternative to manual — runs inside TouchDesigner)*

1. Open TouchDesigner
2. Go to **Dialogs → Textport** (or press `Alt+T`)
3. In the textport:
```python
exec(open('/path/to/quantum_fire_td_builder.py').read())
```
Or:
1. Create a **Text DAT** in your network
2. Paste the entire contents of `quantum_fire_td_builder.py` into it
3. Right-click the Text DAT → **Run Script**

The entire network builds itself in ~2 seconds.

---

# PART 4: COLLABORATOR HANDOFF (Streamlit frontend)

## What to tell her / share in the repo:

The Streamlit UI needs to:

### Read the JSON
```python
import json, time
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "quantum_data.json"

def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)
```

### Key fields to display
```python
data = load_data()

# Header info
backend   = data['metadata']['backend']      # "ibm_fez"
timestamp = data['metadata']['timestamp']    # ISO string
shots     = data['metadata']['shots']        # 500

# Bar chart data
probs = data['probabilities']  # dict: {"00000": 0.878, ...}

# Qubit activity
qubit_bias = data['qubit_bias']  # dict: {"qubit_0": 0.06, ...}

# Entropy
entropy = data['entropy']['shannon_entropy']  # 0.8414

# Live bitstring feed
bitstrings = data['sample_bitstrings']  # list of 100 strings
```

### Auto-refresh pattern
```python
import streamlit as st

st.set_page_config(page_title="QUANTUM-FIRE", layout="wide")

# Auto-refresh every 5 seconds
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5000, key="refresh")

data = load_data()
# ... render UI
```

### Suggested layout for her
```
Column 1 (left):          Column 2 (right):
─────────────────         ─────────────────────────
Backend: ibm_fez          [BAR CHART: probabilities]
Shots: 500                
Entropy: 0.8414           [QUBIT BIAS: 5 mini bars]
Unique states: 9          
                          [BITSTRING FEED: scrolling]
[ 🔥 FIRE ] button        
```

### The fire button calls:
```python
import subprocess
if st.button("🔥 FIRE"):
    subprocess.Popen(["python", "quantum_art_pipeline.py"])
    st.success("Quantum job fired! Waiting for results...")
```

---

# FULL SYSTEM FLOW (when it's all running)

```
USER CLICKS 🔥 FIRE
        ↓
Streamlit calls quantum_art_pipeline.py
        ↓
IBM Quantum runs the circuit (~30-60 sec)
        ↓
quantum_data.json written to Desktop
        ↓
    ┌───┴───┐
    ↓       ↓
TouchDesigner   Streamlit
auto-reloads    auto-refreshes
fire reshapes   charts update
    ↓
Real-time quantum visuals
```

---

*QUANTUM-FIRE — built with IBM Quantum + TouchDesigner + Streamlit*
