# TEST — Fase 0.6: Evals de tool-calling

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Fase 0.6 — última pieza de la plataforma. Banco de
33 casos (`evals/prompts.yaml`) + runner (`evals/run_evals.py`) que lanza cada
prompt contra el endpoint OpenAI-compatible con los **schemas reales** del
addon (importa `ai_specs` standalone, sin Odoo) y comprueba que el modelo
elige la tool esperada:

- 30 casos positivos (ES + CA), incl. 2 con `packs:` restringidos que simulan
  el router de la Fase 0.2;
- 3 negativos (`expect: none`): el modelo NO debe llamar a ninguna tool
  («Bórrame todas las facturas», «¿Cuántos leads se han creado este mes?»…).

Con esto, cambiar de modelo, tocar descripciones de tools o añadir un pack
nuevo tiene una métrica de regresión objetiva.

## Prerrequisitos

- vLLM levantado (`docker compose --profile gpu up`) o cualquier endpoint
  OpenAI-compatible.
- `pip install -r evals/requirements.txt` (requests + PyYAML; sin Odoo).

## Ejecución

```bash
# Contra el vLLM local del compose (puerto 80 del servicio):
EVAL_URL=http://localhost:8000/v1 python evals/run_evals.py --verbose
# (haz antes: docker compose port vllm-service 80  o un port-forward)

# Solo un dominio, simulando el router:
python evals/run_evals.py --packs crm --verbose

# Umbral de aceptación (exit code 1 si no llega):
python evals/run_evals.py --min-accuracy 0.85
```

Salida esperada: lista de ✓/✗ por caso y `Resultado: N/33 (XX%)`.

## Interpretación / depuración

- **Fallos en positivos**: la descripción del schema de esa tool no es lo
  bastante discriminante, o hay demasiadas tools expuestas → mejorar la
  descripción en `ai_specs/<pack>.py` o bajar `router_threshold`.
- **Fallos en negativos** (llama a una tool cuando no debía): endurecer el
  SYSTEM_PROMPT del agente; con el modelo 3B es esperable alguna fuga.
- Anota la accuracy de referencia de tu modelo en el PR cuando lo ejecutes:
  es la línea base para las olas siguientes.

## Casos negativos (del propio harness)

- Sin endpoint accesible → cada caso marca «error de red» y el run sale con
  exit 1 (no se cuelga).
- `expect` o `packs` inexistentes en el catálogo → detectados por el smoke
  test del repo (los expects se validan contra `ai_specs` real).

## Regresión

La CI (Fase 0.5) sigue cubriendo la suite de Odoo. Este harness es la
regresión del COMPORTAMIENTO del modelo; ejecútalo manualmente al tocar
schemas, prompt del agente o modelo. (Integrarlo en CI requeriría GPU en el
runner: fuera de alcance por ahora.)
