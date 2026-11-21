import re
p="src/matheval/templates.py"; s=open(p,encoding="utf-8").read()

def replace_fn(name, new):
    global s
    m = re.search(rf"def {name}\(rng\):.*?(?=\n\n\n\S)", s, re.S)
    assert m, name
    s = s[:m.start()] + new.strip("\n") + s[m.end():]

replace_fn("t7_compra_simple", '''
def t7_compra_simple(rng):
    name = rng.choice(["Ana", "Luis", "Sofía", "Mateo", "Valentina", "Joaquín", "Camila", "Tomás"])
    what, each = rng.choice([("paquetes de figuritas", "uno"), ("cajas de alfajores", "una"), ("bolsas de pan", "una"),
                             ("entradas para la feria", "una"), ("cuadernos", "uno"), ("jugos", "uno")])
    p, q = rng.choice(range(100, 410, 10)), rng.choice(range(3, 16))
    total = p * q
    options, cid = _choices(rng, fmt_ars(total),
                            [(fmt_ars(p + q), "suma_en_lugar_de_multiplicar"),
                             (fmt_ars(p * (q - 1)), "cuenta_una_unidad_menos"),
                             (fmt_ars(total * 10), "error_de_orden_de_magnitud")])
    return dict(stem=f"{name} compra {q} {what} a {fmt_ars(p)} cada {each}. ¿Cuánto paga en total?",
                kind="choice", options=options, correct=cid,
                params={"p": p, "q": q, "answer": str(total), "answer_text": fmt_ars(total)})
''')
replace_fn("t9_resta_simple", '''
def t9_resta_simple(rng):
    a, b = rng.choice(range(300, 2005, 5)), rng.choice(range(50, 905, 5))
    if b >= a:
        raise TemplateError("resta negativa")
    thing = rng.choice(["Un tanque", "Una cisterna", "Una pileta", "Un bidón grande"])
    ans = a - b
    options, cid = _choices(rng, f"{fmt_int(ans)} litros",
                            [(f"{fmt_int(a + b)} litros", "suma_en_lugar_de_restar"),
                             (f"{fmt_int(ans + 10)} litros", "error_de_reagrupacion"),
                             (f"{fmt_int(ans * 10)} litros", "error_de_orden_de_magnitud"),
                             (f"{fmt_int(ans - 100)} litros", "error_de_reagrupacion")])
    return dict(stem=f"{thing} tiene {fmt_int(a)} litros de agua y se usan {fmt_int(b)} litros. ¿Cuántos litros quedan?",
                kind="choice", options=options, correct=cid,
                params={"a": a, "b": b, "answer": str(ans), "answer_text": f"{fmt_int(ans)} litros"})
''')
replace_fn("t4_area_escala", '''
def t4_area_escala(rng):
    k, w, h = rng.choice([200, 500, 1000]), rng.choice(range(2, 10)), rng.choice(range(2, 9))
    real = sp.Rational(w * h * k * k, 10000)
    if real.q != 1:
        raise TemplateError("área no entera")
    real = int(real)
    place = rng.choice(["una habitación", "un patio", "un salón", "una cancha chica"])
    options, cid = _choices(rng, f"{real} m²",
                            [(f"{w * h * k // 100} m²", "escala_lineal_aplicada_al_area"),
                             (f"{w * h} m²", "sin_aplicar_la_escala"),
                             (f"{w * h * k * k // 100} m²", "error_de_unidades")])
    return dict(stem=f"En un plano a escala 1:{k}, {place} rectangular mide {w} cm por {h} cm. ¿Cuál es el área real?",
                kind="choice", options=options, correct=cid,
                params={"k": k, "w": w, "h": h, "answer": str(real), "answer_text": f"{real} m²"})
''')
replace_fn("t5_probabilidad", '''
def t5_probabilidad(rng):
    total = rng.choice([40, 60, 80, 100, 120, 160, 200])
    pcts = rng.choice([(20, 30, 50), (10, 40, 50), (25, 25, 50), (15, 35, 50), (30, 30, 40), (5, 45, 50), (10, 30, 60), (20, 20, 60),
                       (35, 35, 30), (25, 35, 40), (45, 35, 20), (15, 25, 60), (40, 40, 20)])
    counts = [sp.Rational(total * p, 100) for p in pcts]
    if any(c.q != 1 for c in counts):
        raise TemplateError("frecuencias no enteras")
    counts = [int(c) for c in counts]
    topic, header, cats = rng.choice([("cómo viaja al colegio", "Medio", ["bicicleta", "colectivo", "a pie"]),
                                      ("qué deporte prefiere", "Deporte", ["fútbol", "vóley", "básquet"]),
                                      ("qué materia le gusta más", "Materia", ["matemática", "lengua", "ciencias"]),
                                      ("qué fruta elige en el recreo", "Fruta", ["manzana", "banana", "mandarina"])])
    k = rng.randrange(3)
    pct = pcts[k]
    options, cid = _choices(rng, fmt_pct(pct),
                            [(fmt_pct(counts[k]), "cuenta_la_frecuencia_como_porcentaje"),
                             (fmt_pct(100 / 3, 1), "supone_igual_probabilidad"),
                             (fmt_pct(100 - pct), "usa_el_complemento"),
                             (fmt_pct(counts[k] * 100 / (total - counts[k]), 1), "denominador_equivocado")])
    return dict(stem=f"En un curso de {total} estudiantes se preguntó {topic}. Si se elige un estudiante al azar, ¿cuál es la probabilidad de que haya respondido «{cats[k]}»?",
                kind="choice", options=options, correct=cid,
                stimulus={"type": "table", "header": [header, "Estudiantes"], "rows": [[c, str(n)] for c, n in zip(cats, counts)]},
                params={"counts": counts, "total": total, "k": k, "answer": str(pct), "answer_text": fmt_pct(pct)})
''')
replace_fn("t10_monedas", '''
def t10_monedas(rng):
    coins = tuple(sorted(rng.sample([1, 2, 3, 5, 10, 20, 50], 3)))
    amount = rng.choice(range(15, 66, 5))
    n = _count_ways(coins, amount)
    if not 3 <= n <= 16:
        raise TemplateError("cantidad de formas fuera de rango")
    where = rng.choice(["En un kiosco", "En una cantina", "En una feria"])
    return dict(stem=(f"{where} solo hay monedas de {fmt_ars(coins[0])}, {fmt_ars(coins[1])} y {fmt_ars(coins[2])}. "
                      f"¿De cuántas maneras distintas se pueden juntar exactamente {fmt_ars(amount)}? "
                      "Se pueden repetir monedas y el orden no importa."),
                kind="numeric", options=[], correct=n, tolerance=0.0,
                params={"coins": list(coins), "amount": amount, "answer": str(n), "answer_text": str(n)})
''')
replace_fn("t11_patron_baldosas", '''
def t11_patron_baldosas(rng):
    d = rng.choice(range(2, 10))
    a = d + rng.choice(range(1, 10))
    noun, unit = rng.choice([("baldosas", "diseño"), ("fósforos", "figura"), ("cubitos", "torre")])
    return dict(stem=f"Una serie de {unit}s se arma agregando siempre la misma cantidad de {noun} en cada paso. Escribí una expresión "
                     f"para la cantidad de {noun} del {unit} n.",
                kind="expression", options=[], correct=f"{d}*n+{a - d}", variables=["n"],
                stimulus={"type": "table", "header": [unit.capitalize(), noun.capitalize()],
                          "rows": [[str(i + 1), str(a + i * d)] for i in range(3)]},
                params={"a": a, "d": d, "noun": noun, "unit": unit, "answer": f"{d}*n+{a - d}", "answer_text": f"{d}*n+{a - d}"})
''')
replace_fn("t12_cuadrado_crece", '''
def t12_cuadrado_crece(rng):
    k = rng.choice(range(2, 10))
    a = rng.choice([0] + list(range(1, 9)))            # a = 0: cuadrado de lado n; a > 0: rectángulo de lados n y n + a
    if a == 0:
        stem = (f"Un cuadrado tiene un lado de n cm. Si se agranda el lado {k} cm, ¿cuántos cm² aumenta su área? "
                "Escribí una expresión en función de n.")
        correct = f"{2 * k}*n+{k * k}"
    else:
        stem = (f"Un rectángulo tiene lados de n cm y de (n + {a}) cm. Si cada lado se agranda {k} cm, ¿cuántos cm² aumenta su área? "
                "Escribí una expresión en función de n.")
        correct = f"{2 * k}*n+{k * (a + k)}"
    return dict(stem=stem, kind="expression", options=[], correct=correct, variables=["n"],
                params={"k": k, "a": a, "answer": correct, "answer_text": correct})
''')
replace_fn("t15_perimetro", '''
def t15_perimetro(rng):
    w, h = rng.choice(range(5, 31)), rng.choice(range(3, 26))
    if w == h:
        raise TemplateError("cuadrado")
    ans = 2 * (w + h)
    what = rng.choice(["un terreno", "un patio", "una quinta", "una cancha"])
    options, cid = _choices(rng, f"{ans} m", [(f"{w * h} m", "confunde_area_con_perimetro"), (f"{w + h} m", "olvida_duplicar"),
                                             (f"{2 * w * h} m", "confunde_area_con_perimetro")])
    return dict(stem=f"Se quiere cercar {what} rectangular de {w} m por {h} m con alambrado. ¿Cuántos metros de alambrado se necesitan?",
                kind="choice", options=options, correct=cid,
                stimulus={"type": "rect", "width": w, "height": h, "unit": "m"},
                params={"w": w, "h": h, "answer": str(ans), "answer_text": f"{ans} m"})
''')
replace_fn("t17_porcentajes_sucesivos", '''
def t17_porcentajes_sucesivos(rng):
    P, a, b = rng.choice(range(1000, 8001, 500)), rng.choice([5, 10, 15, 20, 25, 30, 40, 50]), rng.choice([5, 10, 15, 20, 25, 30])
    val = sp.Rational(P * (100 + a) * (100 - b), 10000)
    if val.q != 1:
        raise TemplateError("precio no entero")
    ans = int(val)
    thing = rng.choice(["producto", "par de zapatillas", "electrodoméstico", "libro"])
    options, cid = _choices(rng, fmt_ars(ans),
                            [(fmt_ars(P * (100 + a - b) // 100), "suma_porcentajes_sucesivos"),
                             (fmt_ars(P * (100 + a) // 100), "ignora_la_baja"), (fmt_ars(P * (100 - b) // 100), "ignora_el_aumento")])
    return dict(stem=(f"Un {thing} costaba {fmt_ars(P)}. Primero aumentó {a} % y después, con una oferta, bajó {b} % sobre el precio "
                      "ya aumentado. ¿Cuánto cuesta ahora?"),
                kind="choice", options=options, correct=cid,
                params={"P": P, "a": a, "b": b, "answer": str(ans), "answer_text": fmt_ars(ans)})
''')
replace_fn("t20_funcion_tabla", '''
def t20_funcion_tabla(rng):
    m, b0 = rng.choice(range(2, 10)), rng.choice(range(1, 13))
    ys = [m * x + b0 for x in (1, 2, 3)]
    ans = m * 10 + b0
    what, unit = rng.choice([("Un sensor registra una medida", "Medición"), ("Una planta crece", "Semana"), ("Un ahorro aumenta", "Mes")])
    return dict(stem=f"{what} que crece siempre al mismo ritmo, como muestra la tabla. ¿Qué valor va a tener en la fila 10?",
                kind="numeric", options=[], correct=ans, tolerance=0.0,
                stimulus={"type": "table", "header": [unit, "Valor"], "rows": [[str(x), str(y)] for x, y in zip((1, 2, 3), ys)]},
                params={"m": m, "b": b0, "answer": str(ans), "answer_text": str(ans)})
''')
replace_fn("t22_pitagoras", '''
def t22_pitagoras(rng):
    a, b, c = rng.choice([(3, 4, 5), (6, 8, 10), (9, 12, 15), (12, 16, 20), (15, 20, 25), (18, 24, 30), (5, 12, 13), (10, 24, 26),
                          (8, 15, 17), (7, 24, 25), (20, 21, 29)])
    if rng.random() < 0.5:
        a, b = b, a
    leg, h, l = a, b, c
    options, cid = _choices(rng, f"{h} m", [(f"{l - leg} m", "resta_los_lados"), (f"{l + leg} m", "suma_los_lados"),
                                           (f"{h * h} m", "olvida_la_raiz"), (f"{l * leg} m", "multiplica_los_lados")])
    stem = rng.choice([
        f"Una escalera de {l} m está apoyada en una pared vertical. El pie de la escalera está a {leg} m de la pared. ¿A qué altura de la pared llega la escalera?",
        f"Un cable de {l} m va desde la punta de un poste vertical hasta el suelo, a {leg} m de la base del poste. ¿Qué altura tiene el poste?",
        f"Una rampa de {l} m de largo llega a una plataforma. Medida sobre el suelo, la rampa avanza {leg} m. ¿A qué altura está la plataforma?"])
    return dict(stem=stem, kind="choice", options=options, correct=cid,
                params={"leg": leg, "l": l, "answer": str(h), "answer_text": f"{h} m"})
''')
replace_fn("t23_interes_simple", '''
def t23_interes_simple(rng):
    C, t, n = rng.choice([5000, 10000, 20000, 30000, 50000, 100000]), rng.choice(range(3, 13)), rng.choice(range(2, 7))
    if sp.Rational(C * t * n, 100).q != 1:
        raise TemplateError("interés no entero")
    ans = C * t * n // 100
    return dict(stem=(f"Una persona deposita {fmt_ars(C)} a plazo fijo con un interés simple de {t} % anual. "
                      f"¿Cuánto interés gana en {n} años? Escribí solo el número."),
                kind="numeric", options=[], correct=ans, tolerance=0.0,
                params={"C": C, "t": t, "n": n, "answer": str(ans), "answer_text": str(ans)})
''')
replace_fn("t24_mapa", '''
def t24_mapa(rng):
    k, x = rng.choice([250000, 500000, 1000000, 2000000, 5000000]), rng.choice(range(2, 13))
    if sp.Rational(x * k, 100000).q != 1:
        raise TemplateError("distancia no entera")
    ans = x * k // 100000
    return dict(stem=f"En un mapa a escala 1:{fmt_int(k)}, dos ciudades están a {x} cm una de la otra. ¿A cuántos kilómetros están en la realidad?",
                kind="numeric", options=[], correct=ans, tolerance=0.0,
                params={"k": k, "x": x, "answer": str(ans), "answer_text": str(ans)})
''')
old='''    if item.template == "T12":
        k = item.params["k"]
        assert sp.expand((n + k) ** 2 - n ** 2 - to_sympy(item.correct, ["n"])) == 0
        return'''
assert old in s
s=s.replace(old,'''    if item.template == "T12":
        k, a = item.params["k"], item.params["a"]
        grown = (n + k) ** 2 - n ** 2 if a == 0 else (n + k) * (n + a + k) - n * (n + a)
        assert sp.expand(grown - to_sympy(item.correct, ["n"])) == 0
        return''')
old='''                                "verified_with": "sympy"}, **d)'''
assert old in s
s=s.replace(old, old+"\n        item.provenance[\"fp\"] = fingerprint(item)")
s=s.replace('''def generate(template_id: str, seed: int, max_tries: int = 50) -> Item:''','''def fingerprint(item: Item) -> str:
    """Huella del contenido (no del número de semilla): dos ejercicios con la misma huella son el mismo ejercicio."""
    import hashlib, json
    body = json.dumps([item.template, item.stem, sorted(o.text for o in item.options), item.stimulus,
                       item.params.get("answer_text")], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(body.encode()).hexdigest()[:12]


def generate(template_id: str, seed: int, max_tries: int = 50) -> Item:''')
open(p,"w",encoding="utf-8").write(s)

# explicaciones
p="src/matheval/explain.py"; e=open(p,encoding="utf-8").read()
def rep(old,new):
    global e
    assert old in e, old[:60]
    e=e.replace(old,new)
rep('''return ([f"Cada paquete cuesta {_m(p['p'])} y son {p['q']} paquetes.", f"Se multiplica: {p['q']} × {_m(p['p'])} = {_m(tot)}."],''','''return ([f"Cada unidad cuesta {_m(p['p'])} y son {p['q']} unidades.", f"Se multiplica: {p['q']} × {_m(p['p'])} = {_m(tot)}."],''')
rep('''        return ([f"Entre un diseño y el siguiente se agregan siempre {d} baldosas ({a} → {a + d} → {a + 2 * d}).",
                 f"Entonces el diseño n tiene {d} × n baldosas más un ajuste:''','''        noun, unit = p.get("noun", "baldosas"), p.get("unit", "diseño")
        return ([f"Entre un {unit} y el siguiente se agregan siempre {d} {noun} ({a} → {a + d} → {a + 2 * d}).",
                 f"Entonces el {unit} n tiene {d} × n {noun} más un ajuste:''')
rep('''        k = p["k"]
        return ([f"El área inicial es n × n = n².", f"Al agrandar el lado {k} cm, el lado nuevo es n + {k} y el área nueva es (n + {k})² = n² + {2 * k}n + {k * k}.",
                 f"El aumento es el área nueva menos la inicial: {2 * k}n + {k * k}."],
                ["Escribí el área antes y después de agrandar el lado.", "Desarrollá el cuadrado de un binomio y restá n²."])''','''        k, a = p["k"], p["a"]
        if a == 0:
            return ([f"El área inicial es n × n = n².", f"Al agrandar el lado {k} cm, el lado nuevo es n + {k} y el área nueva es (n + {k})² = n² + {2 * k}n + {k * k}.",
                     f"El aumento es el área nueva menos la inicial: {2 * k}n + {k * k}."],
                    ["Escribí el área antes y después de agrandar el lado.", "Desarrollá el cuadrado de un binomio y restá n²."])
        return ([f"El área inicial es n × (n + {a}) = n² + {a}n.", f"Con los lados agrandados {k} cm, el área nueva es (n + {k}) × (n + {a + k}) = n² + {a + 2 * k}n + {k * (a + k)}.",
                 f"El aumento es el área nueva menos la inicial: {2 * k}n + {k * (a + k)}."],
                ["Escribí el área antes y después de agrandar los lados.", "Multiplicá los binomios y restá el área inicial."])''')
rep('''f"La escalera, la pared y el piso forman un triángulo rectángulo: la escalera es la hipotenusa ({l} m).", ''','''f"Los dos lados que forman el ángulo recto y la longitud de {l} m forman un triángulo rectángulo: {l} m es la hipotenusa.", ''')
open(p,"w",encoding="utf-8").write(e)

# adaptativo
p="src/matheval/adaptive.py"; s=open(p,encoding="utf-8").read()
s=s.replace('''@dataclass
class PoolItem:
    id: str
    axis: str
    params: IRTParams
''','''@dataclass
class PoolItem:
    id: str
    axis: str
    params: IRTParams
    fp: str | None = None     # huella del contenido: dos ítems con la misma huella son el mismo ejercicio
''')
a=s.index("def _round_robin"); b=s.index("class MSTSession")
s=s[:a]+'''def _round_robin(cands: list[PoolItem], center: float, size: int, rng: random.Random | None = None, spread: int = 1,
                 used_fp: set | None = None) -> list[PoolItem]:
    """Arma un bloque balanceado por eje con ítems cercanos a `center`. Con `rng`, cada elección se sortea entre los `spread`
    ítems más cercanos de su eje (control de exposición); nunca repite contenido (huella) dentro del diseño."""
    used_fp = used_fp if used_fp is not None else set()
    by_axis = defaultdict(list)
    for it in sorted(cands, key=lambda x: abs(x.params.b - center)):
        by_axis[it.axis].append(it)
    out, axes = [], sorted(by_axis)
    while len(out) < size and any(by_axis.values()):
        for ax in axes:
            lst = by_axis[ax]
            while lst and len(out) < size:
                it = lst.pop(rng.randrange(min(spread, len(lst))) if rng else 0)
                if it.fp is not None and it.fp in used_fp:
                    continue
                if it.fp is not None:
                    used_fp.add(it.fp)
                out.append(it)
                break
    return out


def build_design(pool: list[PoolItem], size: int = 8, center1: float = -1.0,
                 centers2=(-2.0, -1.0, 0.4), centers3=(-2.4, -0.9, 1.0),
                 rng: random.Random | None = None, spread: int = 16) -> MSTDesign:
    left, used_fp = list(pool), set()

    def take(center):
        blk = _round_robin(left, center, size, rng, spread, used_fp)
        ids = {it.id for it in blk}
        left[:] = [x for x in left if x.id not in ids and not (x.fp is not None and x.fp in used_fp)]
        return [it.id for it in blk]

    s1 = take(center1)
    s2 = {k: take(c) for k, c in zip(("low", "mid", "high"), centers2)}
    s3 = {k: take(c) for k, c in zip(("low", "mid", "high"), centers3)}
    return MSTDesign(s1, s2, s3)


def _route(theta: float, cuts) -> str:
    return "low" if theta < cuts[0] else ("high" if theta >= cuts[1] else "mid")


def design_to_dict(d: MSTDesign) -> dict:
    return {"stage1": d.stage1, "stage2": d.stage2, "stage3": d.stage3, "cut2": list(d.cut2), "cut3": list(d.cut3)}


def design_from_dict(x: dict) -> MSTDesign:
    return MSTDesign(x["stage1"], x["stage2"], x["stage3"], tuple(x["cut2"]), tuple(x["cut3"]))


'''+s[b:]
open(p,"w",encoding="utf-8").write(s)
p="src/matheval/directed.py"; s=open(p,encoding="utf-8").read()
def rp(old,new):
    global s
    assert old in s, old[:60]
    s=s.replace(old,new)
rp('''    cat = {"levels": defaultdict(list), "by_template": defaultdict(list), "level_of": {}, "kind": {}}''','''    cat = {"levels": defaultdict(list), "by_template": defaultdict(list), "level_of": {}, "kind": {}, "fp": {}}''')
rp('''            cat["level_of"][it.id], cat["kind"][it.id] = it.target_level, it.kind''','''            cat["level_of"][it.id], cat["kind"][it.id] = it.target_level, it.kind
            cat["fp"][it.id] = it.provenance.get("fp", it.id)''')
rp('''        asked = set(self.administered)
        if self.responses''','''        fp = self.cat.get("fp", {})
        asked_fp = {fp.get(i, i) for i in self.administered}
        asked = set(self.administered)
        if self.responses''')
rp('''            cands = [i for i in self.cat["by_template"].get(_tid(self.responses[-1][0]), []) if i not in asked]''','''            cands = [i for i in self.cat["by_template"].get(_tid(self.responses[-1][0]), []) if i not in asked and fp.get(i, i) not in asked_fp]''')
rp('''            cands = [i for i in self.cat["levels"][lvl] if i not in asked]''','''            cands = [i for i in self.cat["levels"][lvl] if i not in asked and fp.get(i, i) not in asked_fp]''')
open(p,"w",encoding="utf-8").write(s)
p="scripts/generate_bank.py"; s=open(p,encoding="utf-8").read()
old='''for tid in T.SPEC:
    for seed in range(N_PER_TEMPLATE):
        it = T.generate(tid, seed)
        bank.add(it)
        if seed < QTI_PER_TEMPLATE:
            (out / f"{it.id}.xml").write_bytes(item_to_qti(it))'''
assert old in s
s=s.replace(old,'''for tid in T.SPEC:
    seen, seed, n = set(), 0, 0
    while n < N_PER_TEMPLATE and seed < 20 * N_PER_TEMPLATE:          # sin contenido repetido: se descartan semillas duplicadas
        it = T.generate(tid, seed)
        seed += 1
        if it.provenance["fp"] in seen:
            continue
        seen.add(it.provenance["fp"])
        bank.add(it)
        if n < QTI_PER_TEMPLATE:
            (out / f"{it.id}.xml").write_bytes(item_to_qti(it))
        n += 1''')
open(p,"w",encoding="utf-8").write(s)
# pruebas frágiles por orden de importación
for p in ("tests/test_ags.py","tests/test_mock_lms.py"):
    s=open(p,encoding="utf-8").read()
    s=s.replace('__import__("importlib").util.find_spec("flask")','importlib.util.find_spec("flask")')
    if "import importlib.util" not in s: s=s.replace("import os","import importlib.util\nimport os",1)
    open(p,"w",encoding="utf-8").write(s)
p="tests/test_lti_service.py"; s=open(p,encoding="utf-8").read()
s=s.replace("import importlib, os, sys, types, unittest","import importlib.util, os, sys, types, unittest"); open(p,"w",encoding="utf-8").write(s)
