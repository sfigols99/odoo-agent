# TEST — Fase 0.5: CI con módulos OCA

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Fase 0.5. GitHub Actions (`.github/workflows/ci.yml`)
con dos jobs en cada push/PR:

- **static**: compila todo el python y verifica que `ai_specs` sigue siendo un
  paquete puro importable sin Odoo (y que toda tool de escritura tiene
  descripción de confirmación).
- **odoo-tests**: suite completa del addon dentro de la imagen `odoo:18.0` con
  Postgres como service, **instalando los wheels OCA** de
  `requirements-oca.txt` y la BD con `odoo_ai,auditlog,queue_job` (cubre los
  caminos condicionales de las Fases 0.3/0.4).

## Cómo probarlo

1. Empuja cualquier commit a una rama → pestaña **Actions** del repo: ambos
   jobs en verde.
2. Prueba de fuego del guard: rompe temporalmente un test (p. ej. invierte un
   assert de `test_packs.py`), push → el job `odoo-tests` debe fallar con el
   `FAIL:` visible en el log; revierte.
3. Localmente, el equivalente del job es:
   ```bash
   docker compose run --rm odoo bash -c "
     pip3 install --no-deps --break-system-packages -r /dev/stdin <<< 'odoo-addon-queue-job==18.0.*
   odoo-addon-auditlog==18.0.*' 2>/dev/null;
     odoo -d test_ci -i odoo_ai,auditlog,queue_job --test-enable \
       --test-tags /odoo_ai --stop-after-init --log-level=test"
   ```
   (con la imagen ya reconstruida, los wheels ya están dentro y basta el `odoo …`).

## Casos negativos

- Si un wheel OCA no existiera para 18.0, el job falla en «Instalar wheels
  OCA» → revisar la versión en PyPI (`pip index versions odoo-addon-<nombre>`)
  y ajustar el pin de `requirements-oca.txt`.

## Regresión

La propia CI es ahora la regresión automática de todos los TEST.md anteriores
(suite completa del addon en cada push).
