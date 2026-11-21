import test from "node:test";
import assert from "node:assert/strict";
import { topAdvice, ADVICE } from "./tags.ts";

test("agrupa por tema y ordena por frecuencia", () => {
  const out = topAdvice({ suma_en_lugar_de_restar: 2, ignora_el_descuento: 1, lee_otra_fila: 2, desconocida: 9 });
  assert.equal(out[0].advice.topic, "Porcentajes");
  assert.equal(out[0].count, 3);
  assert.equal(out.length, 2);
});

test("cubre todas las etiquetas que producen las plantillas", () => {
  const needed = ["resta_el_porcentaje_como_monto", "informa_el_descuento_y_no_el_total", "suma_en_lugar_de_restar",
    "ignora_el_descuento", "suma_en_lugar_de_multiplicar", "cuenta_una_unidad_menos", "error_de_orden_de_magnitud",
    "lee_otra_fila", "sin_mes_previo", "mayor_valor_en_lugar_de_mayor_variacion", "otra_variacion",
    "escala_lineal_aplicada_al_area", "sin_aplicar_la_escala", "error_de_unidades", "cuenta_la_frecuencia_como_porcentaje",
    "supone_igual_probabilidad", "usa_el_complemento", "denominador_equivocado", "error_de_reagrupacion", "calcula_el_rango", "confunde_area_con_perimetro", "confunde_media_con_mediana", "error_de_calculo", "error_de_lectura_de_la_escala", "error_de_posicion", "ignora_el_aumento", "ignora_la_baja", "lee_otra_barra", "lee_solo_el_valor_final", "no_divide", "no_ordena_los_datos", "olvida_duplicar", "olvida_la_raiz", "resta_los_lados", "suma_los_lados", "suma_porcentajes_sucesivos", "usa_la_media"];
  for (const t of needed) assert.ok(ADVICE[t], t);
});
