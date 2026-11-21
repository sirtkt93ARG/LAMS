# Arreglos de la auditoría (propuestas, no aplicadas en este paquete)

Este paquete es la **versión 0.7 sin modificar**: sus 91 pruebas automáticas pasan. Los arreglos de la auditoría se habían
aplicado en una copia de trabajo que se perdió cuando se reinició el entorno; estos dos scripts los reconstruyen sobre la v0.7.

| Script | Qué hace | Estado |
|---|---|---|
| `parche_a_contenido_y_exposicion.py` | Amplía las variantes de 13 plantillas, agrega huella de contenido, sortea los bloques del examen (control de exposición) y evita repetir contenido en una sesión; corrige dos pruebas frágiles | Se aplicó y las pruebas centrales pasaron (36 pruebas del núcleo) |
| `parche_b_seguridad.py` | Revisión de plantillas solo para curadores, token LTI de un solo uso, guardia de configuración, una respuesta por ejercicio y sesión, invitaciones de red | Se aplicó y compiló, **pero faltan actualizar las pruebas y la interfaz web** (ver más abajo) |

## Cómo aplicarlos

```bash
python docs/arreglos_auditoria/parche_a_contenido_y_exposicion.py   # desde la carpeta platform
python scripts/generate_bank.py
PYTHONPATH=src python -m unittest discover -s tests
```

El parche A usa la ruta `src/matheval/...` relativa a la carpeta `platform`. Antes de aplicar el B hay que agregar el archivo
`api/app/security.py` (copiarlo desde `docs/arreglos_auditoria/security.py`) y, después de aplicarlo, actualizar:

- las pruebas de la API para que los tokens traigan `jti`, para que las revisiones las haga un usuario `admin` y para el flujo de invitaciones de red;
- la web: navegación del rol `admin`, aviso de invitaciones en el panel docente y colores de gráficos con contraste suficiente.

Nada de esto está verificado en conjunto: usarlo como punto de partida y correr las pruebas después de cada paso.
