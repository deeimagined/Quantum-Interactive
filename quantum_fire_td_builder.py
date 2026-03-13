# QUANTUM-FIRE TouchDesigner Network Builder
# Run this inside TouchDesigner: textport or a Text DAT > Run Script
# It builds the entire QUANTUM-FIRE network programmatically.

import td

def build_quantum_fire():
    root = op('/project1')

    # ─────────────────────────────────────────
    # 1. CLEAR existing ops (optional safety)
    # ─────────────────────────────────────────
    for o in root.ops('qfire_*'):
        o.destroy()

    # ─────────────────────────────────────────
    # 2. FILE IN DAT — watches quantum_data.json
    # ─────────────────────────────────────────
    filein = root.create(fileInDAT, 'qfire_filein')
    filein.par.file = '/Users/YOURUSERNAME/Desktop/quantum_data.json'
    filein.par.syncfile = True
    filein.nodeX, filein.nodeY = -800, 400

    # ─────────────────────────────────────────
    # 3. TABLE DATs (parsed data buckets)
    # ─────────────────────────────────────────
    table_probs = root.create(tableDAT, 'qfire_table_probs')
    table_probs.nodeX, table_probs.nodeY = -800, 200

    table_qubits = root.create(tableDAT, 'qfire_table_qubits')
    table_qubits.nodeX, table_qubits.nodeY = -800, 0

    table_meta = root.create(tableDAT, 'qfire_table_meta')
    table_meta.nodeX, table_meta.nodeY = -800, -200

    # ─────────────────────────────────────────
    # 4. PARSER Script DAT
    # ─────────────────────────────────────────
    parser_text = root.create(textDAT, 'qfire_parser_text')
    parser_text.nodeX, parser_text.nodeY = -600, 400
    parser_text.text = '''
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

    # Meta/entropy table
    t3 = op("qfire_table_meta")
    t3.clear()
    t3.appendRow(["key", "value"])
    t3.appendRow(["shannon_entropy",    entropy["shannon_entropy"]])
    t3.appendRow(["normalized_entropy", entropy["normalized_entropy"]])
    t3.appendRow(["shots",              meta["shots"]])
    t3.appendRow(["unique_states",      meta["unique_states"]])
'''

    parser = root.create(scriptDAT, 'qfire_parser')
    parser.par.dat = parser_text
    parser.nodeX, parser_text.nodeY = -400, 400

    # ─────────────────────────────────────────
    # 5. DAT TO CHOPs — convert tables to channels
    # ─────────────────────────────────────────
    dat2chop_probs = root.create(datToChop, 'qfire_dat2chop_probs')
    dat2chop_probs.par.dat         = 'qfire_table_probs'
    dat2chop_probs.par.selectrows  = 'byindex'
    dat2chop_probs.par.fromrow0    = 1   # skip header
    dat2chop_probs.par.selectcols  = 'byname'
    dat2chop_probs.par.colnames    = 'probability'
    dat2chop_probs.nodeX, dat2chop_probs.nodeY = -400, 200

    dat2chop_qubits = root.create(datToChop, 'qfire_dat2chop_qubits')
    dat2chop_qubits.par.dat        = 'qfire_table_qubits'
    dat2chop_qubits.par.selectrows = 'byindex'
    dat2chop_qubits.par.fromrow0   = 1
    dat2chop_qubits.par.selectcols = 'byname'
    dat2chop_qubits.par.colnames   = 'bias'
    dat2chop_qubits.nodeX, dat2chop_qubits.nodeY = -400, 0

    dat2chop_meta = root.create(datToChop, 'qfire_dat2chop_meta')
    dat2chop_meta.par.dat          = 'qfire_table_meta'
    dat2chop_meta.par.selectrows   = 'byindex'
    dat2chop_meta.par.fromrow0     = 1
    dat2chop_meta.par.selectcols   = 'byname'
    dat2chop_meta.par.colnames     = 'value'
    dat2chop_meta.nodeX, dat2chop_meta.nodeY = -400, -200

    # ─────────────────────────────────────────
    # 6. NORMALIZE CHOP — probs 0→1
    # ─────────────────────────────────────────
    norm = root.create(normalizeChop, 'qfire_normalize')
    norm.inputConnectors[0].connect(dat2chop_probs)
    norm.nodeX, norm.nodeY = -200, 200

    # ─────────────────────────────────────────
    # 7. TRAIL CHOP — smooth data transitions
    # ─────────────────────────────────────────
    trail = root.create(trailChop, 'qfire_trail')
    trail.inputConnectors[0].connect(norm)
    trail.par.windowunit  = 'seconds'
    trail.par.windowlength = 0.5
    trail.nodeX, trail.nodeY = 0, 200

    # ─────────────────────────────────────────
    # 8. NOISE TOP — fire base layer
    # ─────────────────────────────────────────
    noise = root.create(noiseTOP, 'qfire_noise')
    noise.par.type        = 'sparse'
    noise.par.roughness   = 0.8   # will be driven by entropy expression
    noise.par.translatey  = tdu.Dependency(0)
    # Expressions set as strings (TD evaluates these each frame)
    noise.par.translatey.expr  = 'absTime.seconds * 0.3'
    noise.par.amp.expr         = "op('qfire_normalize')['chan1'] * 1.5"
    noise.par.roughness.expr   = "op('qfire_dat2chop_meta')['chan1']"  # shannon entropy
    noise.nodeX, noise.nodeY   = 200, 400

    # ─────────────────────────────────────────
    # 9. FEEDBACK TOP
    # ─────────────────────────────────────────
    feedback = root.create(feedbackTOP, 'qfire_feedback')
    feedback.inputConnectors[0].connect(noise)
    feedback.par.top       = 'qfire_feedback'
    feedback.par.opacity   = 0.85
    feedback.nodeX, feedback.nodeY = 400, 400

    # ─────────────────────────────────────────
    # 10. BLUR TOP
    # ─────────────────────────────────────────
    blur = root.create(blurTOP, 'qfire_blur')
    blur.inputConnectors[0].connect(feedback)
    blur.par.filter  = 'gaussian'
    blur.par.sizex   = 8
    blur.par.sizey   = 8
    blur.nodeX, blur.nodeY = 600, 400

    # ─────────────────────────────────────────
    # 11. LEVEL TOP — contrast/brightness
    # ─────────────────────────────────────────
    level = root.create(levelTOP, 'qfire_level')
    level.inputConnectors[0].connect(blur)
    level.par.brightness1 = 1.2
    level.par.contrast    = 1.4
    level.nodeX, level.nodeY = 800, 400

    # ─────────────────────────────────────────
    # 12. RAMP TOP — fire color palette
    # ─────────────────────────────────────────
    ramp = root.create(rampTOP, 'qfire_ramp')
    ramp.par.type = 'linear'
    # Black → deep red → orange → white
    ramp.par.color0r, ramp.par.color0g, ramp.par.color0b = 0.0, 0.0, 0.0
    ramp.par.color1r, ramp.par.color1g, ramp.par.color1b = 0.6, 0.0, 0.0
    ramp.par.color2r, ramp.par.color2g, ramp.par.color2b = 1.0, 0.4, 0.0
    ramp.par.color3r, ramp.par.color3g, ramp.par.color3b = 1.0, 1.0, 0.9
    ramp.nodeX, ramp.nodeY = 800, 200

    # ─────────────────────────────────────────
    # 13. LOOKUP TOP — apply color map
    # ─────────────────────────────────────────
    lookup = root.create(lookupTOP, 'qfire_lookup')
    lookup.inputConnectors[0].connect(level)
    lookup.inputConnectors[1].connect(ramp)
    lookup.nodeX, lookup.nodeY = 1000, 400

    # ─────────────────────────────────────────
    # 14. OUT TOP — final output
    # ─────────────────────────────────────────
    out = root.create(outTOP, 'qfire_out')
    out.inputConnectors[0].connect(lookup)
    out.nodeX, out.nodeY = 1200, 400

    print("✅ QUANTUM-FIRE network built successfully.")
    print("   → Update qfire_filein file path to your Desktop/quantum_data.json")
    print("   → Hit play and run your quantum pipeline to see it fire.")

build_quantum_fire()
