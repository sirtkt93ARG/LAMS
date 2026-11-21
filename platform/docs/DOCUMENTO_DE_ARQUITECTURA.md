# Documento de arquitectura, análisis legal y marco de la plataforma

El documento completo (25 secciones, editable, descargable como Word o PDF desde su menú) está en línea:

- Documento: https://claude.ai/artifact/6NrdwVeAJcWJbnmQHFDThH
- Maqueta de pantallas iniciales (versión 0.1): https://claude.ai/artifact/2J1ugMna22KxLQNYB6YRxV

**Recomendación:** abrí el documento y descargalo como Word o PDF para guardar una copia junto a este paquete.

## Índice de secciones del documento

1. Alcance y advertencia
2. Resumen de ajustes respecto del diseño original
3. Arquitectura revisada (capas, TAO, IA, datos, gobernanza)
4. Contenido y propiedad intelectual (ítems y marca PISA)
5. Licencias de software
6. Datos personales y menores
7. Regulación de IA
8. Marca y nombre
9. Hoja de ruta legal y técnica
10. Documentos legales a preparar
11. Preguntas para tu abogado
12. Catálogo de herramientas (reproductor QTI, LTI, adaptatividad, calidad de IA, tableros, LRS)
13. Decisiones de stack consolidadas
14. Banco de ítems y calidad psicométrica
15. Mercado, competencia y posicionamiento
16. Menores, proveedores de IA y cumplimiento
17. Registro de riesgos
18. Decisiones abiertas
19. Cómo acercarse a PISA sin infringir derechos
20. Fase A como punto de partida (escolar)
21. Herramientas para una plataforma solo de matemática
22. Marco propio de matemática (borrador 0.1)
23. Calibración con la realidad argentina y mundial
24. Revisión del documento de referencia sobre PISA
25. Plan maestro: decisiones vigentes
(Fuentes adicionales al final)

## Decisiones principales (resumen)

- Alcance: Fase A escolar, solo matemática, cercana a PISA con contenido y escala propios (sin usar la marca PISA ni ítems de la OCDE sin permiso).
- Nombre: evitar «PISA» y «LAMS» (este último ya designa a otro sistema); hacer búsqueda de marca.
- Marco: cuatro procesos, cuatro ejes, cuatro contextos y ocho niveles propios (N1 a N8); N4 como hipótesis de nivel mínimo, todavía sin calibrar.
- Evaluación: multietapa de tres etapas y, después, CAT con restricciones.
- Stack: Python con FastAPI, qti3-item-player, PyLTI1p3, Ralph, Keycloak, PostgreSQL con RLS, DuckDB, Langfuse y Tremor; TAO solo aislado o reemplazado; Metabase y GeoGebra descartados por licencia.
- Menores: cuentas gestionadas por la escuela, consentimiento a través de la escuela, sin chat libre con IA, contenido de IA etiquetado y revisado.
