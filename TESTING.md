# TESTING — Cómo probar y depurar la aplicación

Tres niveles de prueba + un flujo de depuración con **Claude Dispatch**. Además,
**todo PR de un punto del roadmap debe incluir un `TEST.md`** (convención al
final de este documento).

---

## 1. Tests automáticos (Odoo `TransactionCase`)

Los tests viven en `addons/odoo_ai/tests/` y se ejecutan dentro del contenedor
de Odoo (no necesitan LLM: el bucle se prueba con el cliente mockeado):

```bash
# Suite completa del addon sobre una BD limpia
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --stop-after-init

# Solo los tests de un archivo/clase (test-tags de Odoo)
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --test-tags /odoo_ai:TestCrmAutomations --stop-after-init
```

Criterio: la suite debe acabar con `0 failed, 0 error(s)` en el log. Cada pack
de tools nuevo añade su propio archivo de tests (uno por tool como mínimo).

## 2. Prueba manual end-to-end (chat)

Con el stack arrancado (`docker compose up` — añade `--profile gpu` si tienes
GPU, o apunta `odoo_ai.vllm_url` a un endpoint OpenAI-compatible):

1. Entra en **Asistente IA → Chat** (http://localhost:8069).
2. Ejecuta los **prompts del `TEST.md`** del PR que estés probando (ver abajo).
3. Para cada escritura, comprueba el ciclo completo:
   - aparece la **tarjeta Confirmar/Cancelar** con una descripción correcta;
   - **Confirmar** crea/modifica el registro real (verifícalo en el módulo);
   - **Cancelar** NO toca datos y la conversación sigue coherente.
4. Repite los prompts clave con un **usuario de permisos limitados**: la tool
   debe devolver el error de permisos en texto, nunca un traceback.

## 3. Evals de tool-calling (Fase 0.6 del roadmap)

Pendiente de implementar: banco de prompts canónicos por pack lanzado contra
vLLM midiendo si el modelo elige la tool y argumentos esperados. Hasta entonces,
la tabla de prompts de cada `TEST.md` hace de banco manual.

---

## Depuración con Claude Dispatch

La depuración de la aplicación se hace **despachando una sesión de Claude**
(Claude Code en web/GitHub) sobre este repo o sobre el PR afectado. Flujo:

1. **Abrir sesión** de Claude apuntando al repo (rama del PR a depurar).
2. **Instrucción inicial recomendada:** indicarle que lea `TESTING.md` y el
   `TEST.md` del PR — ahí están los prompts, el comportamiento esperado y los
   comandos de reproducción. Ejemplo de prompt de despacho:

   > Lee TESTING.md y TEST.md. Reproduce el fallo X: levanta el stack con
   > docker compose, ejecuta la suite y los prompts del TEST.md, localiza la
   > causa y corrígela en esta rama.

3. Claude reproduce con `docker compose`, ejecuta la suite (nivel 1), inspecciona
   logs (`docker compose logs -f odoo`, `docker compose logs vllm-service`) y
   los registros de conversación (`odoo.ai.message`, que guardan cada tool_call
   y su resultado: son la traza de ejecución del agente).
4. El fix se empuja **a la rama del PR**; la sesión puede además suscribirse a
   la actividad del PR para re-ejecutar y corregir si la CI vuelve a fallar.

Puntos de inspección útiles al depurar:

| Síntoma | Dónde mirar |
|---|---|
| El modelo no llama a la tool esperada | descripciones del schema en `TOOL_SPECS`; nº de tools expuestas (modelo pequeño se degrada con >20-25) |
| Tool falla en ejecución | log del contenedor `odoo` (`_logger.exception` en `execute_tool`) y mensaje `tool` guardado en la conversación |
| No aparece la tarjeta de confirmación | `is_write` del spec; `pending_tool_calls` de la conversación |
| Respuestas vacías / 500 | log de vLLM; `odoo_ai.request_timeout`; respuesta cruda en `_call_llm` |
| Tool no disponible | módulo del `requires` instalado? (`_is_available`) |

---

## Convención `TEST.md` (obligatoria en cada PR del roadmap)

Cada PR que implemente un punto del roadmap (ola de módulos o pieza de la
Fase 0) **incluye en la raíz un `TEST.md`** que documenta cómo probar ESA
mejora. El archivo se **reemplaza** en cada PR de ola (el historial queda en
git). Plantilla:

```markdown
# TEST — <nombre del PR / ola del roadmap>

## Alcance
Qué funcionalidad cubre este PR (enlace al punto del ROADMAP.md).

## Prerrequisitos
- Módulos a instalar (p. ej. `odoo-addon-xxx` en requirements-oca.txt)
- Datos de prueba necesarios (clientes, productos, etapas…)
- Perfiles de compose necesarios (gpu/mcp) o endpoint LLM alternativo

## Tests automáticos
Comando(s) exactos y resultado esperado.

## Prompts de prueba (chat)
| # | Prompt | Tool esperada | ¿Escritura? | Resultado esperado |
|---|--------|---------------|-------------|--------------------|
| 1 | "..."  | `tool_name`   | Sí → tarjeta de confirmación | ... |

## Casos negativos
- Cancelar la confirmación → no se modifica nada
- Nombre ambiguo / registro inexistente → mensaje claro, sin traceback
- Usuario sin permisos → error de permisos en texto
- (Si aplica) módulo `requires` no instalado → tool oculta y bloqueada

## Regresión
Prompts de packs anteriores que deben seguir funcionando tras este PR.
```

La tabla de prompts de los `TEST.md` es también la semilla del banco de evals
de la Fase 0.6: escribe los prompts como los escribiría un usuario real.
