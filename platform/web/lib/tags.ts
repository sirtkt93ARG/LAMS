/** Consejos de repaso a partir de las etiquetas de error que modelan los distractores (ver templates.py). */
export type Advice = { topic: string; advice: string };

const T = (topic: string, advice: string): Advice => ({ topic, advice });

const PORC = T("Porcentajes", "Calculá el descuento como una parte del total y recién después restalo del precio.");
const OPER = T("Operaciones con precios", "Fijate qué operación pide cada situación: comprar varias unidades se resuelve multiplicando.");
const TABLAS = T("Lectura de tablas y gráficos", "Antes de responder, marcá en la tabla la fila o los datos que necesitás y compará solo esos.");
const ESCALA = T("Escalas y áreas", "La escala se aplica a cada lado; el área se calcula con las medidas reales, en las unidades que pide el problema.");
const PROB = T("Probabilidad", "La probabilidad es casos favorables sobre casos totales; revisá cuál es el total en la tabla.");

export const ADVICE: Record<string, Advice> = {
  resta_el_porcentaje_como_monto: PORC,
  informa_el_descuento_y_no_el_total: PORC,
  suma_en_lugar_de_restar: PORC,
  ignora_el_descuento: PORC,
  suma_en_lugar_de_multiplicar: OPER,
  cuenta_una_unidad_menos: OPER,
  error_de_reagrupacion: T("Restas con cifras grandes", "Alineá las cifras por posición y revisá cuándo hay que \"pedir prestado\" a la columna siguiente."),
  error_de_orden_de_magnitud: T("Cálculo con cifras grandes", "Estimá primero el orden del resultado (decenas, centenas, miles) para detectar errores."),
  lee_otra_fila: TABLAS,
  sin_mes_previo: TABLAS,
  mayor_valor_en_lugar_de_mayor_variacion: T("Variación en una tabla", "Aumentar más no es lo mismo que tener el valor más alto: restá cada dato al anterior y compará."),
  otra_variacion: T("Variación en una tabla", "Calculá la diferencia entre meses consecutivos y compará todas antes de elegir."),
  escala_lineal_aplicada_al_area: ESCALA,
  sin_aplicar_la_escala: ESCALA,
  error_de_unidades: ESCALA,
  cuenta_la_frecuencia_como_porcentaje: PROB,
  supone_igual_probabilidad: PROB,
  usa_el_complemento: PROB,
  denominador_equivocado: PROB,
  calcula_el_rango: T("Promedio y mediana", "El rango es máximo menos mínimo; la mediana es el dato del medio."),
  confunde_area_con_perimetro: T("Perímetro y área", "El perímetro es la suma de los lados (el borde); el área mide la superficie. Cercar es perímetro."),
  confunde_media_con_mediana: T("Promedio y mediana", "El promedio suma todos los datos y divide; la mediana es el dato del medio una vez ordenados."),
  error_de_calculo: T("Cálculo mental", "Revisá la cuenta: volvé a sumar y dividir con calma."),
  error_de_lectura_de_la_escala: T("Lectura de la escala de un gráfico", "Fijate de cuánto en cuánto avanza cada marca del eje antes de leer un valor."),
  error_de_posicion: T("Promedio y mediana", "Con 7 datos ordenados, la mediana es el cuarto: contá desde un extremo."),
  ignora_el_aumento: T("Porcentajes sucesivos", "El precio de partida de la baja es el precio ya aumentado."),
  ignora_la_baja: T("Porcentajes sucesivos", "Después del aumento hay que aplicar también la baja sobre el precio nuevo."),
  lee_otra_barra: TABLAS,
  lee_solo_el_valor_final: T("Variación en un gráfico", "Para saber cuánto cambió hay que leer los dos puntos y restarlos; no alcanza con leer el último."),
  no_divide: T("Promedio y mediana", "Después de sumar los datos hay que dividir por la cantidad de datos."),
  no_ordena_los_datos: T("Promedio y mediana", "Para hallar la mediana primero hay que ordenar los datos de menor a mayor."),
  olvida_duplicar: T("Perímetro y área", "Un rectángulo tiene dos lados de cada medida: sumá los cuatro lados."),
  olvida_la_raiz: T("Teorema de Pitágoras", "Después de restar los cuadrados falta calcular la raíz cuadrada."),
  resta_los_lados: T("Teorema de Pitágoras", "No se restan las longitudes: se restan los cuadrados y después se calcula la raíz."),
  suma_los_lados: T("Teorema de Pitágoras", "La altura no es la suma de dos medidas: usá el teorema de Pitágoras."),
  suma_porcentajes_sucesivos: T("Porcentajes sucesivos", "Un aumento y una baja no se suman ni se restan: la baja se calcula sobre el precio ya aumentado."),
  usa_la_media: T("Promedio y mediana", "La mediana no es el promedio: es el valor central de los datos ordenados."),
  valor_incorrecto: T("Resolución del problema", "Volvé a leer qué se pide y comprobá tu resultado reemplazando en la situación."),
  expresion_no_equivalente: T("Expresiones algebraicas", "Pensá qué cantidad es fija y cuál cambia con n, y escribí cada parte antes de sumarlas."),
  formato_invalido: T("Cómo escribir la respuesta", "Escribí solo el número, por ejemplo 12 o 12,5."),
  sin_respuesta: T("Respuestas en blanco", "Si no sabés cómo seguir, escribí lo que entendés del problema: ayuda a elegir el próximo ejercicio."),
};

export function topAdvice(tags: Record<string, number>, max = 3): { advice: Advice; count: number }[] {
  const byTopic = new Map<string, { advice: Advice; count: number }>();
  for (const [tag, n] of Object.entries(tags)) {
    const a = ADVICE[tag];
    if (!a) continue;
    const cur = byTopic.get(a.topic);
    byTopic.set(a.topic, { advice: a, count: (cur?.count ?? 0) + n });
  }
  return [...byTopic.values()].sort((x, y) => y.count - x.count).slice(0, max);
}
