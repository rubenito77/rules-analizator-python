def analyze_file(path, top_n_pools=1):
    pooles = defaultdict(lambda: defaultdict(lambda: {"reglas": set(), "horas": [], "threads": Counter()}))
    reglas_pool_set = defaultdict(set)
    reglas_pool_counter = defaultdict(Counter)
    primera_hora_pool = {}
    ultima_hora_pool = {}
    ultima_hora_ne = defaultdict(dict)

    try:
        with open(path, "r", errors="ignore") as f:
            for linea in f:
                hora_seg, hora_str = parse_hora(linea)
                if hora_seg is None:
                    continue

                pool_match = re_pool.search(linea)
                if pool_match:
                    pool = pool_match.group(1)

                    # Obtener thread
                    thread_match = re.search(r'thread-(\d+)', linea)
                    thread_id = f"thread-{thread_match.group(1)}" if thread_match else "thread-unknown"

                    # Obtener regla
                    rule_match = re_rule.search(linea)
                    rule = rule_match.group(1) if rule_match else "SinRule"

                    # Contar reglas y threads
                    reglas_pool_set[pool].add(rule)
                    reglas_pool_counter[pool][rule] += 1
                    pooles[pool][rule]["horas"].append(hora_str)
                    pooles[pool][rule]["threads"][thread_id] += 1

                    # Horas de pool
                    if pool not in primera_hora_pool:
                        primera_hora_pool[pool] = hora_seg
                    ultima_hora_pool[pool] = hora_seg
    except Exception as e:
        return [f"Error leyendo {path}: {e}"]

    if not primera_hora_pool:
        return ["No hay líneas válidas en el log."]

    # Top N pools por duración
    duraciones = {p: ultima_hora_pool[p] - primera_hora_pool[p] for p in primera_hora_pool}
    top_pools = sorted(duraciones.items(), key=lambda x: x[1], reverse=True)[:top_n_pools]

    resumenes = []
    for pool_max, dur in top_pools:
        dur_str = segs_a_hora(dur)
        hora_inicio = segs_a_hora(primera_hora_pool[pool_max])
        hora_fin = segs_a_hora(ultima_hora_pool[pool_max])

        reglas_detalle = []
        duraciones_reglas = {}
        for regla in sorted(reglas_pool_set[pool_max]):
            horas = pooles[pool_max][regla]["horas"]
            inicio = min(horas) if horas else ""
            fin = max(horas) if horas else ""
            reglas_detalle.append({
                "nombre": regla,
                "inicio": inicio,
                "fin": fin,
                "threads": pooles[pool_max][regla]["threads"]
            })

            # Calcular duración de la regla
            if inicio and fin:
                h1 = list(map(int, inicio.split(":")))
                h2 = list(map(int, fin.split(":")))
                dur_s = (h2[0]*3600 + h2[1]*60 + h2[2]) - (h1[0]*3600 + h1[1]*60 + h1[2])
                duraciones_reglas[regla] = dur_s

        # Regla que más duró
        if duraciones_reglas:
            regla_mas_larga_name, dur_seg = max(duraciones_reglas.items(), key=lambda x: x[1])
            regla_mas_larga = {"nombre": regla_mas_larga_name, "duracion": segs_a_hora(dur_seg)}
        else:
            regla_mas_larga = {"nombre": "", "duracion": ""}

        resumen = {
            "pool": pool_max,
            "inicio": hora_inicio,
            "fin": hora_fin,
            "duracion": dur_str,
            "cant_reglas": len(reglas_detalle),
            "reglas": reglas_detalle,
            "regla_mas_larga": regla_mas_larga
        }
        resumenes.append(resumen)

    return resumenes

