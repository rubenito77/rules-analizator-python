#!/usr/bin/env python3
from flask import Flask, render_template, send_file, jsonify
import os, glob, re, datetime, csv
from collections import defaultdict, Counter
from io import StringIO, BytesIO

# ---------------- CONFIGURACIÓN ----------------
LOG_DIR = os.environ.get("LOG_DIR", "/logs")
PORT = int(os.environ.get("PORT", 8081))
TEMPLATE_DIR = os.environ.get("TEMPLATE_DIR", "./templates")

# Flask usa la carpeta de templates externa
app = Flask(__name__, template_folder=TEMPLATE_DIR)

# ---------------- REGEX ----------------
re_pool = re.compile(r'\((pool-\d+)-thread-\d+\)')
re_rule = re.compile(r'Rule\s+([\w\.\-]+)')
time_re = re.compile(r'^.*?(\d{2}):(\d{2}):(\d{2}),(\d{3})')

# ---------------- HELPERS ----------------
def parse_hora(linea):
    match = time_re.search(linea)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        segs = h*3600 + m*60 + s
        return segs, f"{match.group(1)}:{match.group(2)}:{match.group(3)},{match.group(4)}"
    return None, None

def parse_hora_to_seconds(hora_str):
    try:
        h, m, s = map(int, hora_str.split(":"))
        return h*3600 + m*60 + s
    except:
        return 0

def segs_a_hora(segundos):
    h = segundos // 3600
    m = (segundos % 3600) // 60
    s = segundos % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ---------------- ANALIZAR LOG ----------------
def analyze_file(path, top_n_pools=1):
    pooles = defaultdict(lambda: defaultdict(lambda: {"reglas": set(), "horas": []}))
    reglas_pool_set = defaultdict(set)
    reglas_pool_counter = defaultdict(Counter)
    primera_hora_pool = {}
    ultima_hora_pool = {}
    threads_pool = defaultdict(lambda: defaultdict(Counter))  # pool -> regla -> thread -> count

    try:
        with open(path, "r", errors="ignore") as f:
            for linea in f:
                hora_seg, hora_str = parse_hora(linea)
                if hora_seg is None:
                    continue
                pool_match = re_pool.search(linea)
                if pool_match:
                    pool = pool_match.group(1)
                    thread = linea.split(")")[0].split("-thread-")[-1]
                    rule_match = re_rule.search(linea)
                    rule = rule_match.group(1) if rule_match else "SinRule"
                    reglas_pool_set[pool].add(rule)
                    reglas_pool_counter[pool][rule] += 1

                    threads_pool[pool][rule][f"thread-{thread}"] += 1

                    if pool not in primera_hora_pool:
                        primera_hora_pool[pool] = hora_seg
                    ultima_hora_pool[pool] = hora_seg
    except Exception as e:
        return [f"Error leyendo {path}: {e}"]

    if not primera_hora_pool:
        return ["No hay líneas válidas en el log."]

    duraciones = {p: ultima_hora_pool[p] - primera_hora_pool[p] for p in primera_hora_pool}
    top_pools = sorted(duraciones.items(), key=lambda x: x[1], reverse=True)[:top_n_pools]

    resumenes = []
    for pool_max, dur in top_pools:
        dur_str = segs_a_hora(dur)
        hora_inicio = segs_a_hora(primera_hora_pool[pool_max])
        hora_fin = segs_a_hora(ultima_hora_pool[pool_max])
        reglas_unicas = sorted(reglas_pool_set[pool_max])
        ranking_reglas = sorted(reglas_pool_counter[pool_max].items(), key=lambda x: x[1], reverse=True)

        reglas_detalle = []
        regla_mas_larga = {"nombre": "", "duracion": 0}
        for regla_nombre in reglas_unicas:
            inicio = None
            fin = None
            with open(path, "r", errors="ignore") as f:
                for linea in f:
                    if f"Rule {regla_nombre}" in linea and f"({pool_max}" in linea:
                        _, hora_str = parse_hora(linea)
                        if hora_str:
                            if not inicio:
                                inicio = hora_str
                            fin = hora_str
            if inicio and fin:
                dur_seg = parse_hora_to_seconds(fin.split(",")[0]) - parse_hora_to_seconds(inicio.split(",")[0])
            else:
                dur_seg = 0
                inicio = inicio or "00:00:00,000"
                fin = fin or "00:00:00,000"

            if dur_seg > regla_mas_larga.get("duracion",0):
                regla_mas_larga = {"nombre": regla_nombre, "duracion": dur_seg}

            reglas_detalle.append({
                "nombre": regla_nombre,
                "inicio": inicio,
                "fin": fin,
                "duracion_segundos": dur_seg,
                "threads": dict(threads_pool[pool_max][regla_nombre])
            })

        resumen = {
            "pool": pool_max,
            "inicio": hora_inicio,
            "fin": hora_fin,
            "duracion": dur_str,
            "cant_reglas": len(reglas_unicas),
            "reglas": reglas_detalle,
            "ranking_reglas": ranking_reglas,
            "regla_mas_larga": regla_mas_larga
        }
        resumenes.append(resumen)

    return resumenes

# ---------------- RUTAS ----------------
@app.route("/")
def index():
    kieservers = {}
    logs = sorted(glob.glob(os.path.join(LOG_DIR, "*.log")))
    if not logs:
        return render_template("index.html", kieservers={}, timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for log_path in logs:
        pod_name = os.path.basename(log_path).replace(".log","")
        kieservers[pod_name] = analyze_file(log_path, top_n_pools=1)[0]

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("index.html", kieservers=kieservers, timestamp=timestamp)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)  # debug=True permite recarga automática

