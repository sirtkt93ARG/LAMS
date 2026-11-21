"""Plantillas de ítems parametrizadas. Cada ítem se verifica de forma independiente con SymPy."""
from __future__ import annotations
import random
import sympy as sp
from .models import Item, Option, Axis, Process, Context, Status
from .numfmt import fmt_ars, fmt_int, fmt_pct
from .safe_expr import to_sympy

MONTHS = ["Enero", "Febrero", "Marzo", "Abril"]


class TemplateError(Exception):
    """Los parámetros sorteados no cumplen las condiciones; se reintenta con otra semilla."""


def _choices(rng, correct_text, wrongs):
    seen, picked = {correct_text}, []
    for text, tag in wrongs:
        if text not in seen:
            seen.add(text)
            picked.append((text, tag))
    if len(picked) < 3:
        raise TemplateError("distractores insuficientes")
    allopts = [(correct_text, "correcta")] + picked[:3]
    rng.shuffle(allopts)
    options = [Option("ABCD"[i], t, tag) for i, (t, tag) in enumerate(allopts)]
    return options, next(o.id for o in options if o.tag == "correcta")


# ---- Plantillas -----------------------------------------------------------------------
def t8_lectura_tabla(rng):
    names = rng.sample(["Lápiz", "Cuaderno", "Regla", "Goma", "Mochila", "Tijera", "Carpeta"], 4)
    prices = rng.sample(range(80, 900, 10), 4)
    k = rng.randrange(4)
    options, cid = _choices(rng, fmt_ars(prices[k]),
                            [(fmt_ars(prices[j]), "lee_otra_fila") for j in range(4) if j != k])
    return dict(stem=f"La tabla muestra los precios de una librería. ¿Cuánto cuesta el artículo «{names[k]}»?",
                kind="choice", options=options, correct=cid,
                stimulus={"type": "table", "header": ["Artículo", "Precio"],
                          "rows": [[n, fmt_ars(p)] for n, p in zip(names, prices)]},
                params={"names": names, "prices": prices, "k": k, "answer": str(prices[k]), "answer_text": fmt_ars(prices[k])})


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


def t1_descuento(rng):
    p, q = rng.choice([200, 250, 300, 400, 500, 600]), rng.choice([2, 3, 4, 5])
    d = rng.choice([10, 15, 20, 25, 30])
    base = p * q
    disc = sp.Rational(base * d, 100)
    if disc.q != 1:
        raise TemplateError("descuento no entero")
    disc, total = int(disc), base - int(disc)
    options, cid = _choices(rng, fmt_ars(total),
                            [(fmt_ars(base - d), "resta_el_porcentaje_como_monto"),
                             (fmt_ars(disc), "informa_el_descuento_y_no_el_total"),
                             (fmt_ars(base + disc), "suma_en_lugar_de_restar"),
                             (fmt_ars(base), "ignora_el_descuento")])
    return dict(stem=(f"Un local vende cuadernos a {fmt_ars(p)} cada uno. Por la compra de {q} cuadernos "
                      f"hace un descuento del {d} % sobre el total. ¿Cuánto hay que pagar?"),
                kind="choice", options=options, correct=cid,
                params={"p": p, "q": q, "d": d, "answer": str(total), "answer_text": fmt_ars(total)})


def t2_variacion_grafico(rng):
    start = rng.choice(range(40, 90, 5))
    diffs = [rng.choice(range(-10, 31, 5)) for _ in range(3)]
    vals = [start]
    for d in diffs:
        vals.append(vals[-1] + d)
    if diffs.count(max(diffs)) != 1 or min(vals) <= 0:
        raise TemplateError("máximo de variación no único")
    k = diffs.index(max(diffs)) + 1
    wrongs = [(MONTHS[0], "sin_mes_previo")]
    for j in (1, 2, 3):
        if j != k:
            wrongs.append((MONTHS[j], "mayor_valor_en_lugar_de_mayor_variacion" if vals[j] == max(vals) else "otra_variacion"))
    options, cid = _choices(rng, MONTHS[k], wrongs)
    return dict(stem="La tabla muestra las ventas de bicicletas de una tienda. ¿En qué mes aumentaron más las ventas respecto del mes anterior?",
                kind="choice", options=options, correct=cid,
                stimulus={"type": "table", "header": ["Mes", "Ventas"], "rows": [[m, str(v)] for m, v in zip(MONTHS, vals)]},
                params={"values": vals, "answer": str(k), "answer_text": MONTHS[k]})


def t3_tarifa_lineal(rng):
    c, v = rng.choice(range(1000, 2100, 100)), rng.choice(range(100, 400, 50))
    return dict(stem=(f"Un plan de bicicletas compartidas cobra una cuota fija de {fmt_ars(c)} por mes más {fmt_ars(v)} por viaje. "
                      "Escribí una expresión para el costo total en pesos según la cantidad n de viajes."),
                kind="expression", options=[], correct=f"{c}+{v}*n", variables=["n"],
                params={"c": c, "v": v, "answer": f"{c}+{v}*n", "answer_text": f"{c}+{v}*n"})


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


def t6_comparar_planes(rng):
    a, dlt, n0 = rng.choice([150, 200, 250]), rng.choice([50, 100, 150]), rng.choice(range(6, 16))
    b, c = a + dlt, n0 * dlt
    return dict(stem=(f"El plan A cobra una cuota fija de {fmt_ars(c)} por mes más {fmt_ars(a)} por viaje. "
                      f"El plan B no tiene cuota y cobra {fmt_ars(b)} por viaje. ¿Desde cuántos viajes por mes conviene más el plan A?"),
                kind="numeric", options=[], correct=n0 + 1, tolerance=0.0,
                params={"a": a, "b": b, "c": c, "answer": str(n0 + 1), "answer_text": str(n0 + 1)})


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


def _count_ways(coins, amount):
    ways = [1] + [0] * amount
    for c in coins:
        for v in range(c, amount + 1):
            ways[v] += ways[v - c]
    return ways[amount]


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


# ---- Plantillas con gráficos, geometría, estadística, modelos y finanzas (T13 a T24) -------------------
def t13_barras_lectura(rng):
    days = ["Lunes", "Martes", "Miércoles", "Jueves"]
    vals = rng.sample(range(10, 65, 5), 4)
    k = rng.randrange(4)
    options, cid = _choices(rng, str(vals[k]), [(str(vals[j]), "lee_otra_barra") for j in range(4) if j != k])
    return dict(stem=f"El gráfico muestra cuántas bicicletas vendió una tienda cada día. ¿Cuántas vendió el {days[k].lower()}?",
                kind="choice", options=options, correct=cid,
                stimulus={"type": "bar_chart", "title": "Bicicletas vendidas por día", "x_label": "Día", "y_label": "Bicicletas",
                          "categories": days, "values": vals},
                params={"values": vals, "k": k, "answer": str(vals[k]), "answer_text": str(vals[k])})


def t14_lineas_diferencia(rng):
    hours = [6, 9, 12, 15, 18]
    v = [rng.choice(range(8, 16))]
    for _ in range(4):
        v.append(v[-1] + rng.choice([-2, 0, 2, 3, 4, 5]))
    i, j = sorted(rng.sample(range(5), 2))
    ans = v[j] - v[i]
    if ans <= 0:
        raise TemplateError("diferencia no positiva")
    options, cid = _choices(rng, f"{ans} °C", [(f"{v[j] + v[i]} °C", "suma_en_lugar_de_restar"),
                                              (f"{v[j]} °C", "lee_solo_el_valor_final"),
                                              (f"{ans + 2} °C", "error_de_lectura_de_la_escala"),
                                              (f"{abs(ans - 1)} °C", "error_de_lectura_de_la_escala")])
    return dict(stem=f"El gráfico muestra la temperatura durante un día. ¿Cuántos grados subió entre las {hours[i]} h y las {hours[j]} h?",
                kind="choice", options=options, correct=cid,
                stimulus={"type": "line_chart", "title": "Temperatura durante el día", "x_label": "Hora", "y_label": "°C",
                          "categories": [f"{h} h" for h in hours], "values": v},
                params={"values": v, "i": i, "j": j, "answer": str(ans), "answer_text": f"{ans} °C"})


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


def t16_receta(rng):
    p, g, q = rng.choice([2, 4, 5, 6]), rng.choice([100, 150, 200, 250, 300, 400]), rng.choice([8, 10, 12, 15, 20])
    if sp.Rational(g * q, p).q != 1:
        raise TemplateError("resultado no entero")
    ans = g * q // p
    return dict(stem=f"Una receta para {p} personas usa {g} gramos de harina. ¿Cuántos gramos de harina hacen falta para {q} personas?",
                kind="numeric", options=[], correct=ans, tolerance=0.0,
                params={"p": p, "g": g, "q": q, "answer": str(ans), "answer_text": str(ans)})


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


def t18_media(rng):
    m = rng.choice([6, 7, 8, 9])
    base = [rng.choice(range(4, 11)) for _ in range(4)]
    last = 5 * m - sum(base)
    vals = base + [last]
    if not 1 <= last <= 10 or len(set(vals)) < 3:
        raise TemplateError("datos no válidos")
    srt = sorted(vals)
    wrongs = [(str(srt[2]), "confunde_media_con_mediana"), (str(sum(vals)), "no_divide"), (str(m + 1), "error_de_calculo"), (str(m - 1), "error_de_calculo")]
    options, cid = _choices(rng, str(m), wrongs)
    return dict(stem="La tabla muestra las notas de cinco exámenes de una estudiante. ¿Cuál es el promedio de sus notas?",
                kind="choice", options=options, correct=cid,
                stimulus={"type": "table", "header": ["Examen", "Nota"], "rows": [[str(i + 1), str(x)] for i, x in enumerate(vals)]},
                params={"values": vals, "answer": str(m), "answer_text": str(m)})


def t19_mediana(rng):
    vals = rng.sample(range(2, 40), 7)
    srt = sorted(vals)
    med, mean = srt[3], sp.Rational(sum(vals), 7)
    mean_txt = str(sp.floor(mean)) if mean.q == 1 else fmt_pct(float(mean), 1)[:-2]
    options, cid = _choices(rng, str(med), [(str(vals[3]), "no_ordena_los_datos"), (mean_txt, "usa_la_media"),
                                           (str(srt[-1] - srt[0]), "calcula_el_rango"), (str(srt[2]), "error_de_posicion")])
    return dict(stem=f"Se registraron los minutos que tardaron siete estudiantes en llegar al colegio: {', '.join(map(str, vals))}. ¿Cuál es la mediana?",
                kind="choice", options=options, correct=cid,
                params={"values": vals, "answer": str(med), "answer_text": str(med)})


def t20_funcion_tabla(rng):
    m, b0 = rng.choice(range(2, 10)), rng.choice(range(1, 13))
    ys = [m * x + b0 for x in (1, 2, 3)]
    ans = m * 10 + b0
    what, unit = rng.choice([("Un sensor registra una medida", "Medición"), ("Una planta crece", "Semana"), ("Un ahorro aumenta", "Mes")])
    return dict(stem=f"{what} que crece siempre al mismo ritmo, como muestra la tabla. ¿Qué valor va a tener en la fila 10?",
                kind="numeric", options=[], correct=ans, tolerance=0.0,
                stimulus={"type": "table", "header": [unit, "Valor"], "rows": [[str(x), str(y)] for x, y in zip((1, 2, 3), ys)]},
                params={"m": m, "b": b0, "answer": str(ans), "answer_text": str(ans)})


def t21_sistema_cine(rng):
    x, y = rng.choice(range(8, 41)), rng.choice(range(8, 41))
    A, B = rng.choice([1500, 1800, 2000, 2500]), rng.choice([800, 1000, 1200])
    if A <= B or x == y:
        raise TemplateError("datos no adecuados")
    n, R = x + y, A * x + B * y
    return dict(stem=(f"En una función de cine se vendieron {n} entradas y se recaudaron {fmt_ars(R)}. Las entradas de adulto cuestan "
                      f"{fmt_ars(A)} y las de niño {fmt_ars(B)}. ¿Cuántas entradas de adulto se vendieron?"),
                kind="numeric", options=[], correct=x, tolerance=0.0,
                params={"n": n, "R": R, "A": A, "B": B, "answer": str(x), "answer_text": str(x)})


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


def t23_interes_simple(rng):
    C, t, n = rng.choice([5000, 10000, 20000, 30000, 50000, 100000]), rng.choice(range(3, 13)), rng.choice(range(2, 7))
    if sp.Rational(C * t * n, 100).q != 1:
        raise TemplateError("interés no entero")
    ans = C * t * n // 100
    return dict(stem=(f"Una persona deposita {fmt_ars(C)} a plazo fijo con un interés simple de {t} % anual. "
                      f"¿Cuánto interés gana en {n} años? Escribí solo el número."),
                kind="numeric", options=[], correct=ans, tolerance=0.0,
                params={"C": C, "t": t, "n": n, "answer": str(ans), "answer_text": str(ans)})


def t24_mapa(rng):
    k, x = rng.choice([250000, 500000, 1000000, 2000000, 5000000]), rng.choice(range(2, 13))
    if sp.Rational(x * k, 100000).q != 1:
        raise TemplateError("distancia no entera")
    ans = x * k // 100000
    return dict(stem=f"En un mapa a escala 1:{fmt_int(k)}, dos ciudades están a {x} cm una de la otra. ¿A cuántos kilómetros están en la realidad?",
                kind="numeric", options=[], correct=ans, tolerance=0.0,
                params={"k": k, "x": x, "answer": str(ans), "answer_text": str(ans)})


# id: (función, eje, proceso, contexto, nivel objetivo, título)
SPEC = {
    "T9": (t9_resta_simple, Axis.NUMEROS, Process.RESOLVER, Context.COTIDIANO, 2, "Resta con datos explícitos"),
    "T8": (t8_lectura_tabla, Axis.DATOS, Process.INTERPRETAR, Context.COTIDIANO, 1, "Lectura directa de una tabla"),
    "T7": (t7_compra_simple, Axis.NUMEROS, Process.RESOLVER, Context.COTIDIANO, 3, "Compra simple"),
    "T1": (t1_descuento, Axis.NUMEROS, Process.RESOLVER, Context.COTIDIANO, 4, "Precio con descuento"),
    "T2": (t2_variacion_grafico, Axis.DATOS, Process.INTERPRETAR, Context.SOCIAL, 4, "Mayor variación en una tabla"),
    "T3": (t3_tarifa_lineal, Axis.FUNCIONES, Process.MODELIZAR, Context.LABORAL, 5, "Tarifa lineal"),
    "T4": (t4_area_escala, Axis.GEOMETRIA, Process.RESOLVER, Context.COTIDIANO, 5, "Área y escala en un plano"),
    "T5": (t5_probabilidad, Axis.DATOS, Process.INTERPRETAR, Context.CIENTIFICO, 6, "Probabilidad con tabla"),
    "T6": (t6_comparar_planes, Axis.FUNCIONES, Process.RESOLVER, Context.LABORAL, 6, "Punto de equilibrio entre planes"),
    "T10": (t10_monedas, Axis.NUMEROS, Process.RESOLVER, Context.COTIDIANO, 7, "Conteo sistemático con monedas"),
    "T11": (t11_patron_baldosas, Axis.FUNCIONES, Process.MODELIZAR, Context.COTIDIANO, 7, "Expresión de un patrón"),
    "T12": (t12_cuadrado_crece, Axis.GEOMETRIA, Process.MODELIZAR, Context.CIENTIFICO, 8, "Generalización: crecimiento del área"),
    "T13": (t13_barras_lectura, Axis.DATOS, Process.INTERPRETAR, Context.SOCIAL, 2, "Lectura de un gráfico de barras"),
    "T14": (t14_lineas_diferencia, Axis.DATOS, Process.INTERPRETAR, Context.CIENTIFICO, 4, "Variación en un gráfico de líneas"),
    "T15": (t15_perimetro, Axis.GEOMETRIA, Process.RESOLVER, Context.COTIDIANO, 3, "Perímetro de un terreno"),
    "T16": (t16_receta, Axis.NUMEROS, Process.RESOLVER, Context.COTIDIANO, 4, "Proporcionalidad en una receta"),
    "T17": (t17_porcentajes_sucesivos, Axis.NUMEROS, Process.RESOLVER, Context.LABORAL, 6, "Aumento y rebaja sucesivos"),
    "T18": (t18_media, Axis.DATOS, Process.RESOLVER, Context.SOCIAL, 4, "Promedio de datos"),
    "T19": (t19_mediana, Axis.DATOS, Process.RESOLVER, Context.SOCIAL, 5, "Mediana de datos"),
    "T20": (t20_funcion_tabla, Axis.FUNCIONES, Process.MODELIZAR, Context.CIENTIFICO, 5, "Valor de una función lineal desde una tabla"),
    "T21": (t21_sistema_cine, Axis.NUMEROS, Process.MODELIZAR, Context.LABORAL, 7, "Sistema de ecuaciones en un contexto"),
    "T22": (t22_pitagoras, Axis.GEOMETRIA, Process.RESOLVER, Context.COTIDIANO, 6, "Teorema de Pitágoras en una escalera"),
    "T23": (t23_interes_simple, Axis.NUMEROS, Process.RESOLVER, Context.LABORAL, 6, "Interés simple"),
    "T24": (t24_mapa, Axis.GEOMETRIA, Process.RESOLVER, Context.SOCIAL, 4, "Distancia real en un mapa"),
}


def fingerprint(item: Item) -> str:
    """Huella del contenido (no del número de semilla): dos ejercicios con la misma huella son el mismo ejercicio."""
    import hashlib, json
    body = json.dumps([item.template, item.stem, sorted(o.text for o in item.options), item.stimulus,
                       item.params.get("answer_text")], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(body.encode()).hexdigest()[:12]


def generate(template_id: str, seed: int, max_tries: int = 50) -> Item:
    fn, axis, process, context, level, title = SPEC[template_id]
    for attempt in range(max_tries):
        rng = random.Random(f"{template_id}:{seed}:{attempt}")
        try:
            d = fn(rng)
        except TemplateError:
            continue
        item = Item(id=f"{template_id}-{seed}", template=template_id, axis=axis, process=process,
                    context=context, target_level=level, status=Status.VERIFICADO,
                    provenance={"method": "plantilla", "template": template_id, "title": title, "seed": seed,
                                "verified_with": "sympy"}, **d)
        item.provenance["fp"] = fingerprint(item)
        verify_item(item)
        return item
    raise TemplateError(f"no se pudo generar {template_id} con semilla {seed}")


# ---- Verificación independiente ------------------------------------------------------
def _expected(item: Item):
    p, t = item.params, item.template
    R = sp.Rational
    if t == "T8":
        return R(p["prices"][p["k"]])
    if t == "T7":
        return R(p["p"] * p["q"])
    if t == "T9":
        return R(p["a"] - p["b"])
    if t == "T10":   # recuento por fuerza bruta, independiente de la programación dinámica de la plantilla
        c1, c2, c3 = p["coins"]
        return R(sum(1 for i in range(p["amount"] // c1 + 1) for j in range(p["amount"] // c2 + 1)
                     for k in range(p["amount"] // c3 + 1) if i * c1 + j * c2 + k * c3 == p["amount"]))
    if t == "T1":
        return R(p["p"] * p["q"]) * (1 - R(p["d"], 100))
    if t == "T2":
        v = p["values"]
        diffs = [v[i] - v[i - 1] for i in (1, 2, 3)]
        assert diffs.count(max(diffs)) == 1
        return R(diffs.index(max(diffs)) + 1)
    if t == "T4":
        return R(p["w"] * p["k"], 100) * R(p["h"] * p["k"], 100)
    if t == "T5":
        return R(p["counts"][p["k"]], p["total"]) * 100
    if t == "T6":
        n = sp.Symbol("n", integer=True)
        sol = sp.solve_univariate_inequality(p["c"] + p["a"] * n < p["b"] * n, n, relational=False)
        return R(sp.floor(sol.inf) + 1) if sol.inf == int(sol.inf) else R(sp.ceiling(sol.inf))
    if t == "T13":
        return R(p["values"][p["k"]])
    if t == "T14":
        return R(p["values"][p["j"]] - p["values"][p["i"]])
    if t == "T15":
        return R(2 * (p["w"] + p["h"]))
    if t == "T16":
        return R(p["g"]) * R(p["q"]) / R(p["p"])
    if t == "T17":
        return R(p["P"]) * (1 + R(p["a"], 100)) * (1 - R(p["b"], 100))
    if t == "T18":
        return R(sum(p["values"]), 5)
    if t == "T19":
        return R(sorted(p["values"])[3])
    if t == "T20":
        return R(p["m"] * 10 + p["b"])
    if t == "T21":
        x, y = sp.symbols("x y")
        sol = sp.solve([x + y - p["n"], p["A"] * x + p["B"] * y - p["R"]], [x, y])
        return R(sol[x])
    if t == "T22":
        return sp.sqrt(R(p["l"]) ** 2 - R(p["leg"]) ** 2)
    if t == "T23":
        return R(p["C"]) * R(p["t"], 100) * p["n"]
    if t == "T24":
        return R(p["x"]) * R(p["k"], 100000)
    raise KeyError(t)


def verify_item(item: Item) -> None:
    """Lanza AssertionError si la clave no coincide con un recálculo independiente."""
    n = sp.Symbol("n")
    if item.template == "T3":
        assert sp.simplify(to_sympy(item.correct, ["n"]) - (item.params["c"] + item.params["v"] * n)) == 0
        assert to_sympy(item.correct, ["n"]).subs(n, 8) == item.params["c"] + 8 * item.params["v"]
        return
    if item.template == "T11":
        a, d, e = item.params["a"], item.params["d"], to_sympy(item.correct, ["n"])
        assert [e.subs(n, i) for i in (1, 2, 3)] == [a, a + d, a + 2 * d]
        assert [int(r[1]) for r in item.stimulus["rows"]] == [a, a + d, a + 2 * d]
        return
    if item.template == "T12":
        k, a = item.params["k"], item.params["a"]
        grown = (n + k) ** 2 - n ** 2 if a == 0 else (n + k) * (n + a + k) - n * (n + a)
        assert sp.expand(grown - to_sympy(item.correct, ["n"])) == 0
        return
    exp = _expected(item)
    assert sp.Rational(item.params["answer"]) == exp, f"{item.id}: clave {item.params['answer']} != {exp}"
    if item.kind == "choice":
        correct_opts = [o for o in item.options if o.id == item.correct]
        assert len(correct_opts) == 1 and correct_opts[0].text == item.params["answer_text"]
        assert len({o.text for o in item.options}) == len(item.options) == 4
        assert sum(1 for o in item.options if o.tag == "correcta") == 1
    elif item.kind == "numeric":
        assert float(item.correct) == float(exp)
    if item.stimulus and item.stimulus.get("type") in ("bar_chart", "line_chart"):
        assert len(item.stimulus["categories"]) == len(item.stimulus["values"])
