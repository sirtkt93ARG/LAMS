"""Construye data/observatory/pisa_agregados.csv con el registro de procedencia de cada dato.
Los valores de 2000 a 2022 se transcribieron de la OCDE (PISA 2022 Results, Vol. I, Anexo D, «Snapshot of mathematics,
reading and science results»). Los de 2025 y los porcentajes bajo el nivel 2 vienen de reportes de prensa y de resúmenes:
están marcados como «secundaria» y deben contrastarse con las tablas oficiales antes de publicarse."""
import csv, pathlib

OECD_VOL1 = "https://www.oecd.org/en/publications/pisa-2022-results-volume-i_53f23881-en/full-report/component-29.html"
SRC_VOL1 = "OCDE, PISA 2022 Results (Vol. I), Anexo D"
SRC_AVG = "OCDE vía data.gov.uk y EMS Magazine 133 (2024)"
URL_AVG = "https://social-mobility.data.gov.uk/drivers_of_social_mobility/educational_opportunities_and_quality_of_schooling/availability_of_high-quality_school_education"
SRC_2025 = "Prensa y resúmenes sobre PISA 2025 (8/9/2026): chequeado.com, perfil.com, OCDE"
URL_2025 = "https://chequeado.com/nota/pruebas-pisa-2025-8-de-cada-10-estudiantes-argentinos-no-alcanza-el-nivel-minimo-en-matematica-y-el-59-tampoco-en-lectura"

M, R, S = "matematica", "lectura", "ciencias"
LATAM, REF, AVG = "America Latina", "Referencia", "Promedio OCDE"
D = {  # (entidad, grupo): {dominio: {ciclo: media}}
 ("Argentina", LATAM): {M: {2006: 381, 2009: 388, 2012: 388, 2018: 379, 2022: 378},
                        R: {2000: 418, 2006: 374, 2009: 398, 2012: 396, 2018: 402, 2022: 401},
                        S: {2006: 391, 2009: 401, 2012: 406, 2018: 404, 2022: 406}},
 ("Brasil", LATAM): {M: {2003: 356, 2006: 370, 2009: 386, 2012: 389, 2015: 377, 2018: 384, 2022: 379},
                     R: {2000: 396, 2003: 403, 2006: 393, 2009: 412, 2012: 407, 2015: 407, 2018: 413, 2022: 410},
                     S: {2006: 390, 2009: 405, 2012: 402, 2015: 401, 2018: 404, 2022: 403}},
 ("Chile", LATAM): {M: {2006: 411, 2009: 421, 2012: 423, 2015: 423, 2018: 417, 2022: 412},
                    R: {2000: 410, 2006: 442, 2009: 449, 2012: 441, 2015: 459, 2018: 452, 2022: 448},
                    S: {2006: 438, 2009: 447, 2012: 445, 2015: 447, 2018: 444, 2022: 444}},
 ("Colombia", LATAM): {M: {2006: 370, 2009: 381, 2012: 376, 2015: 390, 2018: 391, 2022: 383},
                       R: {2006: 385, 2009: 413, 2012: 403, 2015: 425, 2018: 412, 2022: 409},
                       S: {2006: 388, 2009: 402, 2012: 399, 2015: 416, 2018: 413, 2022: 411}},
 ("Costa Rica", LATAM): {M: {2009: 409, 2012: 407, 2015: 400, 2018: 402, 2022: 385},
                         R: {2009: 443, 2012: 441, 2015: 427, 2018: 426, 2022: 415},
                         S: {2009: 430, 2012: 429, 2015: 420, 2018: 416, 2022: 411}},
 ("Finlandia", REF): {M: {2003: 544, 2006: 548, 2009: 541, 2012: 519, 2015: 511, 2018: 507, 2022: 484}},
 ("Alemania", REF): {M: {2003: 503, 2006: 504, 2009: 513, 2012: 514, 2015: 506, 2018: 500, 2022: 475}},
 ("Francia", REF): {M: {2003: 511, 2006: 496, 2009: 497, 2012: 495, 2015: 493, 2018: 495, 2022: 474}},
 ("Canadá", REF): {M: {2003: 532, 2006: 527, 2009: 527, 2012: 518, 2015: 516, 2018: 512, 2022: 497}},
 ("Australia", REF): {M: {2003: 524, 2006: 520, 2009: 514, 2012: 504, 2015: 494, 2018: 491, 2022: 487}},
 ("Hong Kong (China)", REF): {M: {2003: 550, 2006: 547, 2009: 555, 2012: 561, 2015: 548, 2018: 551, 2022: 540}},
}
OECD_AVG_M = {2003: 499, 2006: 490, 2009: 492, 2012: 488, 2015: 485, 2018: 487, 2022: 472}
NOTES = {("Argentina", M, 2022): "Pasó de prueba en papel a computadora en 2022 (nota de la OCDE)",
         ("Argentina", R, 2022): "Pasó de prueba en papel a computadora en 2022 (nota de la OCDE)",
         ("Argentina", S, 2022): "Pasó de prueba en papel a computadora en 2022 (nota de la OCDE)"}
rows = []


def add(cycle, dom, ent, grp, mean=None, below=None, top=None, src=SRC_VOL1, url=OECD_VOL1, q="oficial_ocde", note=""):
    rows.append(dict(ciclo=cycle, dominio=dom, entidad=ent, grupo=grp, media=mean if mean is not None else "", error_estandar="", bajo_nivel2_se="",
                     bajo_nivel2=below if below is not None else "", niveles5y6=top if top is not None else "",
                     fuente=src, url=url, calidad=q, calidad_bajo_nivel2=(q if (below is not None) else ""), nota=note))


for (ent, grp), doms in D.items():
    for dom, pts in doms.items():
        for c, v in pts.items():
            add(c, dom, ent, grp, v, note=NOTES.get((ent, dom, c), ""))
for c, v in OECD_AVG_M.items():
    add(c, M, "OCDE (promedio de tendencia)", AVG, v, src=SRC_AVG, url=URL_AVG, q="secundaria",
        note="Promedio de los países con datos comparables en todos los ciclos; no es el promedio de la OCDE de cada informe")
# PISA 2025 (fuentes secundarias)
add(2025, M, "Argentina", LATAM, 367, src=SRC_2025, url=URL_2025, q="secundaria")
add(2025, R, "Argentina", LATAM, 389, src=SRC_2025, url=URL_2025, q="secundaria")
add(2025, S, "Argentina", LATAM, 393, src=SRC_2025, url=URL_2025, q="secundaria")
add(2025, M, "OCDE (promedio de tendencia)", AVG, 463, below=35, top=8, src=SRC_2025, url=URL_2025, q="secundaria",
    note="Promedio OCDE 2025 informado por la OCDE; la comparabilidad con la serie de tendencia debe verificarse")
add(2025, M, "Singapur", REF, 563, below=11, top=37, src=SRC_2025, url=URL_2025, q="secundaria")
add(2025, M, "B-S-J-Z (China)", REF, 612, src=SRC_2025, url=URL_2025, q="secundaria")
# Porcentaje de estudiantes de Argentina bajo el nivel 2 en matemática (informes de prensa que citan a la OCDE)
for c, v in {2006: 64, 2009: 64, 2012: 66, 2018: 69, 2022: 73, 2025: 76}.items():
    for r in rows:
        if r["entidad"] == "Argentina" and r["dominio"] == M and r["ciclo"] == c:
            r["bajo_nivel2"], r["calidad_bajo_nivel2"] = v, "secundaria"       # la media conserva su calidad oficial
            r["nota"] = (r["nota"] + "; " if r["nota"] else "") + "El porcentaje bajo el nivel 2 proviene de prensa que cita a la OCDE"
out = pathlib.Path("data/observatory/pisa_agregados.csv")
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(sorted(rows, key=lambda r: (r["dominio"], r["entidad"], r["ciclo"])))
print(f"{len(rows)} observaciones en {out}")
