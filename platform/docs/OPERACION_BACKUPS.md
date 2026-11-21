# Copias de seguridad y restauración de PostgreSQL

Este procedimiento es una base operativa para PostgreSQL 16. No equivale a un plan de continuidad completo ni certifica backups de producción. Antes de usarlo con datos reales, la institución debe definir RPO, RTO, retención, cifrado, responsables y ubicación de las copias.

## Qué cubre y qué no

`scripts/postgres_backup.py backup` crea una copia lógica consistente de una base con `pg_dump` en formato custom. La valida con `pg_restore --list`, calcula SHA-256 y publica el directorio de forma atómica. Los archivos quedan con permisos locales restrictivos (directorio 0700 y archivos 0600).

El backup **no incluye** roles globales, contraseñas, parámetros del servidor, certificados, secretos de la aplicación, archivos fuera de PostgreSQL, el estado de Keycloak ni datos almacenados en un LRS externo. Las ACL de los objetos de la base sí se conservan; el rol `matheval_app` debe existir en el destino. Provisioná los roles y credenciales por un canal seguro antes de restaurar.

El archivo no se cifra por sí mismo. Guardalo en un volumen cifrado y cifrá también cualquier copia externa o transferencia. No subas backups con datos de estudiantes al repositorio, a tickets ni a servicios personales.

## Crear una copia

Requisitos: cliente PostgreSQL (`pg_dump`, `pg_restore`, `psql`) de la misma versión mayor que el servidor o una posterior compatible; Python 3.10+; acceso de lectura a la base.

Desde `platform/`:

```bash
export DATABASE_URL='postgresql://usuario:contraseña@servidor:5432/matheval?sslmode=verify-full'
python scripts/postgres_backup.py backup --output-dir /ruta/segura/backups
```

Preferí inyectar `DATABASE_URL` desde un gestor de secretos. Evitá escribir credenciales en el historial del shell. El programa convierte la URL en variables libpq y usa un archivo pgpass temporal con permisos 0600; elimina ese archivo al terminar. No pasa la contraseña como argumento de `pg_dump`.

Salida esperada: un directorio con nombre `matheval-AAAAmmddTHHMMSSZ/`, que contiene:

- `database.dump`: archivo custom de PostgreSQL.
- `manifest.json`: base, fecha, versión de servidor/cliente, tamaño y SHA-256.

Copiá el directorio completo a almacenamiento externo cifrado. Conservá el manifiesto junto al dump. El proceso no rota ni elimina backups antiguos: aplicá la retención aprobada por la institución mediante una tarea separada, y nunca borres la última copia restaurable conocida.

## Restaurar en un destino aislado

La restauración es deliberadamente conservadora: exige el nombre exacto de la base como confirmación, verifica manifiesto y SHA-256, comprueba que exista `matheval_app` y **rechaza destinos que ya contengan objetos de usuario**. No ejecuta `--clean`, no borra tablas existentes ni sobrescribe bases activas.

1. Creá una base PostgreSQL vacía en un entorno aislado, preferentemente de staging.
2. Provisioná previamente el rol `matheval_app` con `LOGIN NOBYPASSRLS`, contraseña administrada por secretos y los atributos necesarios. No reutilices credenciales de ejemplo.
3. Inyectá `DATABASE_URL` apuntando exclusivamente a esa base vacía.
4. Ejecutá:

```bash
export DATABASE_URL='postgresql://admin:contraseña@staging:5432/matheval_restore?sslmode=verify-full'
python scripts/postgres_backup.py restore \
  --backup /ruta/segura/backups/matheval-AAAAmmddTHHMMSSZ \
  --confirm-database matheval_restore
```

La restauración usa `pg_restore --single-transaction --exit-on-error`, sin cambiar propietarios ni descartar ACL. Si falla, la transacción se revierte. Después comprueba que existan las tablas principales.

5. Verificá el estado de migraciones y la versión de la aplicación; revisá extensiones, grants, RLS y conectividad.
6. Arrancá la API en staging y comprobá `/healthz`, `/readyz`, login, una práctica sintética, panel docente autorizado y aislamiento entre dos escuelas de prueba.
7. Registrá duración, resultado, versión del backup y cualquier incidencia. No declares restauración probada sin haber ejecutado el procedimiento completo.

**Nunca apuntes este procedimiento de prueba a producción.** Para recuperar producción, primero elaborá un plan de corte, respaldo del estado actual, aprobación del responsable y estrategia de reversión. Esta herramienta no automatiza el cambio de tráfico.

## Frecuencia, retención y pruebas

La frecuencia de backup y la retención dependen del RPO/RTO y de las obligaciones de la institución; no hay valores universales seguros. Programá la ejecución con el scheduler de la infraestructura (cron, systemd timer u orquestador) y alertá ante código de salida distinto de cero, falta de copia reciente o espacio insuficiente.

Como mínimo operativo:

- Mantener copias cifradas en una ubicación separada del servidor de base de datos.
- Restringir acceso a personal autorizado y auditar lecturas/restauraciones.
- Supervisar antigüedad, tamaño, espacio libre y resultado de cada backup.
- Probar restauraciones periódicamente en un entorno aislado y medir el RTO real.
- Definir cómo expiran y se eliminan también las copias que contienen datos personales, incluidas réplicas y almacenamiento externo.
- Considerar WAL/PITR si el RPO requerido es menor que el intervalo entre copias lógicas; este script no configura archivado WAL ni recuperación a un instante.
- Respaldar por separado configuración, secretos, certificados, Keycloak y cualquier almacenamiento externo; no guardar secretos dentro del manifiesto.

## Límites conocidos

- La copia es lógica de una sola base; no es un backup físico del clúster ni incluye roles globales.
- SHA-256 detecta corrupción accidental o modificación, pero no sustituye una firma ni protege frente a un atacante que pueda modificar dump y manifiesto.
- Los permisos 0600/0700 protegen el filesystem local; no cifran el contenido.
- La prueba automatizada de este script cubre validación del manifiesto y guardas de seguridad. La compatibilidad real de `pg_dump`/`pg_restore` y una restauración end-to-end deben probarse contra PostgreSQL de staging antes de producción.
