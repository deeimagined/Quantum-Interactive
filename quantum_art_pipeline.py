"""
quantum_art_pipeline.py
QUANTUM-FIRE — IBM Quantum backend
Fires a real quantum job and saves structured output to Desktop/quantum_data.json
GitHub: github.com/deeimagined/Quantum-Interactive
"""

import json
import os
import math
from datetime import datetime
from pathlib import Path

# ── Qiskit imports ──────────────────────────────────────────────────────────
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_ibm_runtime import SamplerOptions

# ── CONFIG ───────────────────────────────────────────────────────────────────
IBM_CHANNEL   = "ibm_quantum"       # or "ibm_cloud"
IBM_TOKEN     = os.getenv("IBM_QUANTUM_TOKEN", "YOUR_TOKEN_HERE")
BACKEND_NAME  = "ibm_fez"           # change to your preferred backend
SHOTS         = 500
N_QUBITS      = 5
OUTPUT_PATH   = Path.home() / "Desktop" / "quantum_data.json"


# ── BUILD CIRCUIT ─────────────────────────────────────────────────────────────
def build_circuit(n_qubits: int) -> QuantumCircuit:
    """
    5-qubit entangled circuit with Hadamard + CNOT chain.
    Creates superposition across all qubits — maximizes state diversity.
    """
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    qc.measure(range(n_qubits), range(n_qubits))
    return qc


# ── RUN JOB ───────────────────────────────────────────────────────────────────
def run_quantum_job(circuit: QuantumCircuit):
    """Connect to IBM Quantum, run circuit, return counts dict."""
    service = QiskitRuntimeService(channel=IBM_CHANNEL, token=IBM_TOKEN)
    backend = service.backend(BACKEND_NAME)

    transpiled = transpile(circuit, backend=backend, optimization_level=1)

    options = SamplerOptions()
    options.default_shots = SHOTS

    sampler = Sampler(backend=backend, options=options)
    job     = sampler.run([transpiled])

    print(f"  Job submitted: {job.job_id()}")
    print(f"  Waiting for results from {BACKEND_NAME}...")

    result      = job.result()
    pub_result  = result[0]
    counts_raw  = pub_result.data.c.get_counts()

    return job.job_id(), counts_raw


# ── PROCESS RESULTS ───────────────────────────────────────────────────────────
def process_counts(counts: dict, shots: int) -> dict:
    """
    From raw counts, derive:
      - probabilities per state
      - per-qubit bias (marginal probability qubit = 1)
      - Shannon entropy
      - sample bitstrings (first 100)
    """
    total = sum(counts.values())

    # Probabilities
    probabilities = {
        state: round(count / total, 4)
        for state, count in sorted(counts.items(), key=lambda x: -x[1])
    }

    # Qubit bias — marginal probability each qubit measured |1>
    n = len(next(iter(counts)))
    qubit_bias = {}
    for q in range(n):
        ones = sum(count for state, count in counts.items() if state[-(q+1)] == '1')
        qubit_bias[f"qubit_{q}"] = round(ones / total, 4)

    # Shannon entropy
    probs_list = list(probabilities.values())
    shannon = -sum(p * math.log2(p) for p in probs_list if p > 0)
    max_entropy = math.log2(len(probs_list)) if len(probs_list) > 1 else 1
    normalized_entropy = round(shannon / max_entropy, 4) if max_entropy > 0 else 0

    # Sample bitstrings — weighted random sample from counts
    import random
    population = []
    for state, count in counts.items():
        population.extend([state] * count)
    sample_bitstrings = random.sample(population, min(100, len(population)))

    return {
        "probabilities":    probabilities,
        "qubit_bias":       qubit_bias,
        "shannon_entropy":  round(shannon, 4),
        "normalized_entropy": normalized_entropy,
        "sample_bitstrings": sample_bitstrings,
    }


# ── SAVE OUTPUT ───────────────────────────────────────────────────────────────
def save_output(job_id: str, counts: dict, processed: dict):
    """Write final structured JSON to Desktop for TouchDesigner + Streamlit."""
    output = {
        "metadata": {
            "timestamp":     datetime.now().isoformat(),
            "backend":       BACKEND_NAME,
            "job_id":        job_id,
            "shots":         SHOTS,
            "unique_states": len(counts),
        },
        "measurement_counts": counts,
        "probabilities":      processed["probabilities"],
        "qubit_bias":         processed["qubit_bias"],
        "sample_bitstrings":  processed["sample_bitstrings"],
        "entropy": {
            "shannon_entropy":    processed["shannon_entropy"],
            "normalized_entropy": processed["normalized_entropy"],
        },
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ quantum_data.json saved → {OUTPUT_PATH}")
    print(f"   States measured:   {len(counts)}")
    print(f"   Shannon entropy:   {processed['shannon_entropy']}")
    print(f"   Dominant state:    {list(processed['probabilities'].items())[0]}")

    return output


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  QUANTUM-FIRE pipeline starting...")
    print("=" * 50)

    print("\n[1/3] Building quantum circuit...")
    circuit = build_circuit(N_QUBITS)
    print(circuit.draw())

    print("\n[2/3] Running IBM Quantum job...")
    job_id, counts = run_quantum_job(circuit)

    print("\n[3/3] Processing results...")
    processed = process_counts(counts, SHOTS)
    save_output(job_id, counts, processed)

    print("\n  TouchDesigner will auto-reload quantum_data.json")
    print("  QUANTUM-FIRE is live.\n")


if __name__ == "__main__":
    main()
