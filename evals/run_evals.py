#!/usr/bin/env python3
"""Evals de tool-calling contra un endpoint OpenAI-compatible (Fase 0.6).

Lanza los prompts de prompts.yaml con los schemas reales del addon (importados
de ai_specs, sin necesitar Odoo) y comprueba que el modelo elige la tool
esperada. Sirve para detectar regresiones al añadir packs o cambiar de modelo.

Uso:
    python evals/run_evals.py                       # contra http://localhost:8000/v1
    EVAL_URL=http://otro:80/v1 python evals/run_evals.py
    python evals/run_evals.py --packs crm,stock --verbose
    python evals/run_evals.py --min-accuracy 0.85

Requisitos: pip install requests pyyaml  (sin dependencia de Odoo).
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons" / "odoo_ai"))
import ai_specs  # noqa: E402  (paquete puro del addon)

# Mismo espíritu que el SYSTEM_PROMPT del agente (resumido para el eval).
SYSTEM_PROMPT = (
    "Eres un asistente integrado en el ERP Odoo de la empresa. Para responder "
    "con datos reales USA SIEMPRE las herramientas; nunca inventes cifras ni "
    "nombres. Llama como máximo a UNA herramienta por turno. Si ninguna "
    "herramienta sirve para la petición, NO llames a ninguna y explica el "
    "límite. Responde en el idioma del usuario."
)


def schemas_for(packs=None):
    specs = ai_specs.TOOL_SPECS
    if packs:
        specs = [s for s in specs if s["pack"] in packs]
    return [s["schema"] for s in specs]


def run_case(base_url, model, temperature, case, default_packs, timeout):
    packs = case.get("packs") or default_packs
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": case["prompt"]},
        ],
        "tools": schemas_for(packs),
        "tool_choice": "auto",
    }
    resp = requests.post(f"{base_url}/chat/completions", json=payload,
                         timeout=timeout)
    resp.raise_for_status()
    msg = resp.json()["choices"][0]["message"]
    calls = msg.get("tool_calls") or []
    got = calls[0]["function"]["name"] if calls else None
    expected = case.get("expect")
    expected = None if expected in (None, "none") else expected
    ok = got == expected
    detail = ""
    if ok and expected and case.get("expect_args"):
        try:
            got_args = json.loads(calls[0]["function"].get("arguments") or "{}")
        except ValueError:
            got_args = {}
        for k, v in case["expect_args"].items():
            if got_args.get(k) != v:
                ok = False
                detail = f"args: esperaba {k}={v!r}, llegó {got_args.get(k)!r}"
                break
    return ok, got, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default=str(ROOT / "evals" / "prompts.yaml"))
    parser.add_argument("--packs", default="",
                        help="csv de packs a exponer por defecto (vacío = todos)")
    parser.add_argument("--min-accuracy", type=float, default=0.8)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    base_url = os.environ.get("EVAL_URL", "http://localhost:8000/v1").rstrip("/")
    model = os.environ.get("EVAL_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    temperature = float(os.environ.get("EVAL_TEMPERATURE", "0.1"))
    default_packs = [p.strip() for p in args.packs.split(",") if p.strip()] or None

    with open(args.cases, encoding="utf-8") as fh:
        cases = yaml.safe_load(fh)

    print(f"Endpoint: {base_url}  modelo: {model}  casos: {len(cases)}\n")
    passed, failures = 0, []
    for i, case in enumerate(cases, 1):
        try:
            ok, got, detail = run_case(
                base_url, model, temperature, case, default_packs, args.timeout)
        except requests.RequestException as exc:
            ok, got, detail = False, None, f"error de red: {exc}"
        mark = "✓" if ok else "✗"
        if ok:
            passed += 1
        else:
            failures.append((case["prompt"], case.get("expect"), got, detail))
        if args.verbose or not ok:
            print(f"{mark} [{i:02d}] {case['prompt'][:60]!r}"
                  f" esperado={case.get('expect')} obtenido={got} {detail}")

    accuracy = passed / len(cases) if cases else 0.0
    print(f"\nResultado: {passed}/{len(cases)} ({accuracy:.0%})"
          f" — umbral {args.min_accuracy:.0%}")
    if failures:
        print(f"Fallos: {len(failures)} (anótalos: son la cola de mejora de "
              f"descripciones de tools o del prompt del agente)")
    sys.exit(0 if accuracy >= args.min_accuracy else 1)


if __name__ == "__main__":
    main()
