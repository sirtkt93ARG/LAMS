"""Resolución paso a paso y pistas para cada plantilla. Los números se calculan a partir de los parámetros del ítem
y cada explicación se autoverifica contra la clave."""
from __future__ import annotations
from .models import Item
from .numfmt import fmt_ars, fmt_int


def _m(x): return fmt_ars(x)


def _explain(it: Item):
    p, t = it.params, it.template
    if t == "T1":
        base = p["p"] * p["q"]; disc = base * p["d"] // 100; tot = base - disc; assert tot == int(p["answer"])
        return ([f"Calculá el total sin descuento: {p['q']} × {_m(p['p'])} = {_m(base)}.",
                 f"El descuento es el {p['d']} % de {_m(base)}: {_m(base)} × {p['d']} ÷ 100 = {_m(disc)}.",
                 f"Restá el descuento al total: {_m(base)} − {_m(disc)} = {_m(tot)}."],
                ["Empezá por el precio total antes del descuento.", "El porcentaje se calcula sobre el total, no sobre el precio de uno."])
    if t == "T2":
        v = p["values"]; d = [v[i] - v[i - 1] for i in (1, 2, 3)]; names = ["Febrero", "Marzo", "Abril"]
        return ([f"Restá cada mes al anterior: " + "; ".join(f"{n}: {v[i + 1]} − {v[i]} = {d[i]}" for i, n in enumerate(names)) + ".",
                 f"El mayor aumento es {max(d)}, en {names[d.index(max(d))]}."],
                ["Aumentar más no es lo mismo que tener el valor más alto.", "Calculá la diferencia entre cada mes y el anterior."])
    if t == "T3":
        return ([f"La cuota fija no cambia: {_m(p['c'])}.", f"Cada viaje suma {_m(p['v'])}, así que n viajes cuestan {p['v']} × n.",
                 f"El total es la suma: {p['c']} + {p['v']} × n."],
                ["Separá lo que se paga una sola vez de lo que se paga por cada viaje.", "Probá con n = 1 y n = 2 para comprobar tu expresión."])
    if t == "T4":
        rw, rh = p["w"] * p["k"] // 100, p["h"] * p["k"] // 100; a = rw * rh; assert a == int(p["answer"])
        return ([f"Convertí cada lado con la escala: {p['w']} cm × {p['k']} = {p['w'] * p['k']} cm = {rw} m y {p['h']} cm × {p['k']} = {rh} m.",
                 f"Calculá el área real: {rw} m × {rh} m = {a} m²."],
                ["La escala se aplica a cada lado, no al área.", "Pasá los centímetros a metros antes de multiplicar."])
    if t == "T5":
        n, tot = p["counts"][p["k"]], p["total"]; pct = n * 100 // tot; assert pct == int(p["answer"])
        return ([f"Casos favorables: {n}. Casos totales: {tot}.", f"Probabilidad = {n} ÷ {tot} = {n / tot:.2f}, que es {pct} %."],
                ["Probabilidad es casos favorables dividido casos totales.", "El total de casos es la cantidad de estudiantes del curso."])
    if t == "T6":
        a, b, c = p["a"], p["b"], p["c"]; n0 = c // (b - a); assert n0 + 1 == int(p["answer"])
        return ([f"El plan A cuesta {c} + {a} × n y el plan B cuesta {b} × n.", f"Cuestan lo mismo cuando {c} + {a}n = {b}n, es decir {c} = {b - a}n.",
                 f"Entonces n = {c} ÷ {b - a} = {n0}: con {n0} viajes cuestan igual.", f"El plan A conviene con más de {n0} viajes, o sea desde {n0 + 1}."],
                ["Escribí el costo de cada plan en función de la cantidad de viajes.", "Buscá cuántos viajes hacen que ambos costos sean iguales."])
    if t == "T7":
        tot = p["p"] * p["q"]; assert tot == int(p["answer"])
        return ([f"Cada paquete cuesta {_m(p['p'])} y son {p['q']} paquetes.", f"Se multiplica: {p['q']} × {_m(p['p'])} = {_m(tot)}."],
                ["Comprar varias unidades del mismo precio se resuelve con una multiplicación."," Multiplicá la cantidad por el precio de uno."])
    if t == "T8":
        return ([f"Buscá en la tabla la fila de «{p['names'][p['k']]}».", f"Ahí figura el precio {_m(p['prices'][p['k']])}."],
                ["Ubicá primero el nombre del artículo en la primera columna.", "El precio está en la misma fila."])
    if t == "T9":
        r = p["a"] - p["b"]; assert r == int(p["answer"])
        return ([f"Lo que queda es lo que había menos lo que se usó.", f"{fmt_int(p['a'])} − {fmt_int(p['b'])} = {fmt_int(r)} litros."],
                ["¿Hay que sumar o restar?", "Alineá las cifras: unidades con unidades, decenas con decenas."])
    if t == "T10":
        c1, c2, c3, amt = *p["coins"], p["amount"]
        combos = [(i, j, k) for i in range(amt // c1 + 1) for j in range(amt // c2 + 1) for k in range(amt // c3 + 1) if i * c1 + j * c2 + k * c3 == amt]
        assert len(combos) == int(p["answer"])
        lst = "; ".join(f"{i}×${c1} + {j}×${c2} + {k}×${c3}" for i, j, k in combos)
        return ([f"Ordená el conteo: fijá cuántas monedas de {_m(c3)} usás (0, 1, 2…) y completá con las otras.", f"Las combinaciones posibles son: {lst}.",
                 f"En total hay {len(combos)} maneras."],
                ["Hacé una lista ordenada para no repetir ni olvidar combinaciones.", "Empezá por la moneda más grande."])
    if t == "T11":
        a, d = p["a"], p["d"]
        return ([f"Entre un diseño y el siguiente se agregan siempre {d} baldosas ({a} → {a + d} → {a + 2 * d}).",
                 f"Entonces el diseño n tiene {d} × n baldosas más un ajuste: en n = 1 hay {a}, y {d} × 1 = {d}.", f"El ajuste es {a} − {d} = {a - d}, así que la expresión es {d}n + {a - d}."],
                ["Calculá cuánto crece la cantidad en cada paso.", "Ese crecimiento multiplica a n; después ajustá con el primer valor."])
    if t == "T12":
        k = p["k"]
        return ([f"El área inicial es n × n = n².", f"Al agrandar el lado {k} cm, el lado nuevo es n + {k} y el área nueva es (n + {k})² = n² + {2 * k}n + {k * k}.",
                 f"El aumento es el área nueva menos la inicial: {2 * k}n + {k * k}."],
                ["Escribí el área antes y después de agrandar el lado.", "Desarrollá el cuadrado de un binomio y restá n²."])
    if t == "T13":
        return ([f"Buscá la barra de {p['k'] and ''}ese día en el eje horizontal y seguí hasta lo alto de la barra.", f"El valor leído en el eje vertical es {p['values'][p['k']]}."],
                ["Ubicá el día en el eje horizontal.", "Leé el número del eje vertical al que llega la barra."])
    if t == "T14":
        v, i, j = p["values"], p["i"], p["j"]; r = v[j] - v[i]; assert r == int(p["answer"])
        return ([f"Leé la temperatura en cada hora: {v[i]} °C al principio y {v[j]} °C al final.", f"Restá: {v[j]} − {v[i]} = {r} °C."],
                ["Leé los dos puntos del gráfico por separado.", "Para saber cuánto subió, restá el valor final menos el inicial."])
    if t == "T15":
        r = 2 * (p["w"] + p["h"]); assert r == int(p["answer"])
        return ([f"El alambrado rodea el terreno, así que hay que sumar los cuatro lados.", f"2 × ({p['w']} + {p['h']}) = {r} m."],
                ["Cercar es recorrer el borde: no es el área.", "Un rectángulo tiene dos lados iguales de cada medida."])
    if t == "T16":
        r = p["g"] * p["q"] // p["p"]; assert r == int(p["answer"])
        return ([f"Para 1 persona hacen falta {p['g']} ÷ {p['p']} = {p['g'] / p['p']:g} gramos.", f"Para {p['q']} personas: {p['g'] / p['p']:g} × {p['q']} = {r} gramos."],
                ["Averiguá primero cuánto hace falta para una sola persona.", "Después multiplicá por la cantidad de personas."])
    if t == "T17":
        P, a, b = p["P"], p["a"], p["b"]; up = P * (100 + a) // 100; r = up * (100 - b) // 100; assert r == int(p["answer"])
        return ([f"Después del aumento: {_m(P)} × {100 + a} ÷ 100 = {_m(up)}.", f"La baja se calcula sobre el precio nuevo: {_m(up)} × {100 - b} ÷ 100 = {_m(r)}."],
                ["Los porcentajes sucesivos no se suman: cada uno se calcula sobre el precio anterior.", "Resolvé primero el aumento y después la baja."])
    if t == "T18":
        v = p["values"]; r = sum(v) // 5; assert r == int(p["answer"])
        return ([f"Sumá las notas: {' + '.join(map(str, v))} = {sum(v)}.", f"Dividí por la cantidad de notas: {sum(v)} ÷ 5 = {r}."],
                ["El promedio usa todas las notas.", "Se suma todo y se divide por cuántas son."])
    if t == "T19":
        v = p["values"]; s = sorted(v); assert s[3] == int(p["answer"])
        return ([f"Ordená los datos de menor a mayor: {', '.join(map(str, s))}.", f"Son 7 datos: la mediana es el del medio (el cuarto): {s[3]}."],
                ["Antes de buscar el del medio hay que ordenar.", "Con 7 datos, el del medio es el cuarto."])
    if t == "T20":
        m, b = p["m"], p["b"]; r = m * 10 + b; assert r == int(p["answer"])
        return ([f"Entre una medición y la siguiente el valor crece {m}.", f"En la medición 1 vale {m + b}, así que el valor es {m} × n + {b}.", f"Para n = 10: {m} × 10 + {b} = {r}."],
                ["Calculá cuánto crece el valor en cada medición.", "Escribí una regla para cualquier medición y reemplazá n por 10."])
    if t == "T21":
        n, R, A, B = p["n"], p["R"], p["A"], p["B"]; x = int(p["answer"]); y = n - x; assert A * x + B * y == R
        return ([f"Sea x las entradas de adulto e y las de niño: x + y = {n} y {A}x + {B}y = {R}.", f"De la primera, y = {n} − x. Reemplazá: {A}x + {B}({n} − x) = {R}.",
                 f"Resolvé: {A - B}x = {R - B * n}, entonces x = {x}."],
                ["Escribí dos ecuaciones: una con la cantidad de entradas y otra con el dinero.", "Despejá una incógnita de la primera y reemplazala en la segunda."])
    if t == "T22":
        l, leg = p["l"], p["leg"]; h = int(p["answer"]); assert l * l == leg * leg + h * h
        return ([f"La escalera, la pared y el piso forman un triángulo rectángulo: la escalera es la hipotenusa ({l} m).", f"h² = {l}² − {leg}² = {l * l} − {leg * leg} = {h * h}.", f"h = √{h * h} = {h} m."],
                ["Dibujá el triángulo rectángulo.", "Se busca un cateto: restá los cuadrados."])
    if t == "T23":
        C, tt, n = p["C"], p["t"], p["n"]; r = C * tt * n // 100; assert r == int(p["answer"])
        return ([f"El interés de un año es el {tt} % de {_m(C)}: {_m(C)} × {tt} ÷ 100 = {_m(C * tt // 100)}.", f"En {n} años: {_m(C * tt // 100)} × {n} = {_m(r)}."],
                ["Con interés simple cada año se gana lo mismo.", "Calculá el interés de un año y multiplicalo por los años."])
    if t == "T24":
        k, x = p["k"], p["x"]; r = x * k // 100000; assert r == int(p["answer"])
        return ([f"Cada centímetro del mapa son {fmt_int(k)} cm reales: {x} × {fmt_int(k)} = {fmt_int(x * k)} cm.", f"Pasá a kilómetros (1 km = 100.000 cm): {fmt_int(x * k)} ÷ 100.000 = {r} km."],
                ["Multiplicá la distancia del mapa por la escala.", "Convertí centímetros a kilómetros al final."])
    raise KeyError(t)


def explain(item: Item) -> dict:
    steps, hints = _explain(item)
    return {"steps": steps + [f"Respuesta: {item.params['answer_text']}"], "hints": [h.strip() for h in hints]}
