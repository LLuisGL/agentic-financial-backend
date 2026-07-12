# agentic-financial-backend

 **EN ARCHIVO .ENV.EXAMPLE AHI SE DEBE COLOCAR LA KEY DE GEMINIS**

Primero que todo, utilcie en el Backend (FastAPI) que conecta un bot de WhatsApp en Jelou con la asistencia
inteligente para el, ayudandome con claude este cubre las 3 historias de usuario:

1. Ingreso asistido y reutilización de antecedentes
2. Validación y siguiente acción guiada
3. Preparación de negociación y cierre asistido

Todas las acciones reguladas (liquidación, transferencia, endoso) quedan
siempre como **propuesta / alerta / solicitud de aprobacion**: el backend
nunca las ejecuta automáticamente por lo que tengo entendido

## Arquitectura
Aqui claude me dio una estrucutra de como esta formado todo, por lo que he estado 
revisando y analizando:
- `main.py`: expone `/health` y `/webhook` (extracción de datos de la nota
  de crédito en PDF con Gemini) y monta los routers de `app/`.
- `app/database.py`: conexión SQLite (SQLAlchemy). Archivo en
  `data/agentic_financial.db`, se crea solo al arrancar.
- `app/models.py`: `Cliente`, `Titulo` (nota de crédito), `Caso`
  (expediente), `EventoCaso` (bitácora), `DebidaDiligencia`, `ListaRiesgo`
  (PEP/sanciones simulada), `Negociacion`.
- `app/validations.py`: motor de validaciones de la HU2 (existencia, saldo,
  estado, bloqueos, duplicados, riesgo) y priorización del siguiente paso.
- `app/negociacion.py`: cálculo de la propuesta económica y generación del
  borrador de negociación (HU3), con las fórmulas del procedimiento:
  `VE = VN * P / 100`, `CBVQ = VE * 0.09%`, `Ccv = VE * 0.5%`,
  `Vneto = VE - CBVQ - Ccv - OTROS`.
- `app/seed_data.py`: datos de demostración (clientes, títulos, lista de
  riesgo) para poder mostrar el flujo de extremo a extremo sin integración
  real al SRI/DECEVALE.
- `app/routers/clientes.py`, `app/routers/casos.py`: endpoints REST.


## Configuración
La configuarcion para arrancar seria estos comandos, obviamente ahi debemos 
colocar una key de geminis para poder utilizarlo 
```bash
pip install -r requirements.txt
cp .env.example .env  # agrega tu GENAI_APIKEY (https://aistudio.google.com/apikey)
uvicorn main:app --reload
```


## ENDPOINTS
Me lo divide todo en las historias de usuario y las validaciones que realizo 
jonnathan, por lo que quedo asi para claude:

### HU1 — Ingreso asistido y reutilización de antecedentes

- `POST /clientes/buscar` — busca por `ruc_cedula`, `razon_social` o
  `numero_titulo`. Devuelve cada dato reutilizable con su **fuente, fecha y
  estado**, más los títulos y casos anteriores del cliente.
- `POST /casos` — crea el expediente. Recibe los datos del cliente/título y
  una lista `campos: [{campo, valor, accion}]` donde `accion` es
  `confirmar | editar | rechazar`. Los campos rechazados **no se guardan**.
- `GET /clientes/{id}` — detalle de un cliente con sus títulos y casos.

### HU2 — Validación y siguiente acción guiada

- `POST /casos/{id}/validar` — valida existencia, saldo, estado y bloqueos
  del título; detecta duplicados (otro caso abierto con el mismo título) y
  coincidencias en la lista de riesgo/PEP; devuelve la lista de pendientes
  priorizada, con la evidencia que debe revisar el operador, y un
  `siguiente_accion_sugerida` (`SOLICITAR_DOCUMENTO`, `ACTUALIZAR_DATO`,
  `ENVIAR_A_CUMPLIMIENTO`, `PREPARAR_ORDEN` o `CONTINUAR`).
- `POST /casos/{id}/diligencia` — registra el checklist de debida diligencia
  (identidad, capacidad legal, representación legal, KYC, origen de fondos)
  y cruza automáticamente contra la lista de riesgo. Resultado:
  `APROBADO | PENDIENTE | RECHAZADO`.

### HU3 — Preparación de negociación y cierre asistido

- `POST /casos/{id}/negociacion/propuesta` — recibe `precio_negociacion_pct`
  (y opcionalmente `otros_costos`, `vigencia_autorizacion`,
  `instrucciones_especiales`, `cuenta_destino`), calcula la propuesta
  económica y genera un borrador de ficha de negociación para que el
  operador lo revise.
- `POST /casos/{id}/negociacion/{negociacion_id}/aprobar` — el operador
  aprueba el borrador.
- `POST /casos/{id}/cierre` — recibe `accion: LIQUIDACION | TRANSFERENCIA |
  ENDOSO`. Solo registra la solicitud de aprobación; **no ejecuta nada**.
- `GET /casos/{id}` — expediente completo: estado, próxima acción,
  responsable, observaciones, título, diligencia, negociaciones y bitácora
  de eventos.
- `GET /casos?estado=&ruc_cedula=` — lista de casos con filtros.


## Flujo típico desde Jelou
Lo que entendi sobre el flujo que hace JELOU:
1. Cliente envía la nota de crédito por WhatsApp → Jelou llama a
   `/webhook` → se extraen los datos del PDF.
2. Jelou llama a `/clientes/buscar` con el RUC extraído para mostrar
   antecedentes al operador.
3. El operador confirma/edita/rechaza los datos → `POST /casos` crea el
   expediente.
4. `POST /casos/{id}/validar` y `POST /casos/{id}/diligencia` guían los
   controles pendientes.
5. `POST /casos/{id}/negociacion/propuesta` genera la propuesta económica y
   el borrador; el operador la aprueba con `.../aprobar`.
6. `POST /casos/{id}/cierre` deja la liquidación/transferencia/endoso como
   solicitud de aprobación humana.

