import json
import logging
import re

import requests

from odoo import models

_logger = logging.getLogger(__name__)

# Valores por defecto si no existen los ir.config_parameter (ver data/).
DEFAULTS = {
    "odoo_ai.vllm_url": "http://vllm-service/v1",
    "odoo_ai.model": "Qwen/Qwen2.5-7B-Instruct",
    "odoo_ai.max_tool_iterations": "6",
    "odoo_ai.temperature": "0.1",
    "odoo_ai.request_timeout": "120",
    # Fase 0.2 — selección dinámica de tools:
    # packs habilitados ("all" o csv: "crm,sale") y umbral a partir del cual
    # se enruta por dominio antes de exponer tools al modelo.
    "odoo_ai.enabled_packs": "all",
    "odoo_ai.router_threshold": "20",
}

SYSTEM_PROMPT = """Eres un asistente integrado en el ERP Odoo de la empresa. \
Ayudas con inventario/stock, CRM y ventas, facturación y compras.

Reglas:
- Para responder con datos reales USA SIEMPRE las herramientas; nunca inventes \
cifras, nombres ni IDs.
- Llama como máximo a UNA herramienta por turno y razona paso a paso.
- Las acciones de escritura (crear/confirmar/registrar) requieren confirmación \
del usuario; el sistema la pide automáticamente, tú solo propón la acción con \
los datos correctos.
- Responde de forma concisa y en el mismo idioma que el usuario.
- Si una herramienta devuelve un error de permisos, explícaselo con claridad.
"""


class AiAgent(models.AbstractModel):
    _name = "odoo.ai.agent"
    _description = "Runtime del Asistente IA (bucle de tool-calling)"

    # ------------------------------------------------------------------
    # Motor — invocado por odoo.ai.conversation (que es la entrada RPC).
    # Se ejecuta como el usuario actual => las tools heredan sus permisos.
    # ------------------------------------------------------------------
    def run_chat(self, conv, user_message):
        # Si había una acción pendiente y el usuario escribe otra cosa,
        # se cancela (manteniendo el historial válido).
        self._cancel_pending(conv)
        conv._add_message("user", content=user_message or "")
        return self._run(conv)

    def run_execute(self, conv, confirm):
        """Ejecuta (o cancela) la acción de escritura pendiente y continúa."""
        pending = json.loads(conv.pending_tool_calls or "[]")
        if not pending:
            return {"type": "reply", "content": "No hay ninguna acción pendiente."}
        tc = pending.pop(0)
        result = self._resolve_tool_call(tc, confirm=bool(confirm))
        conv._add_message(
            "tool", content=result, tool_call_id=tc.get("id"),
            name=tc.get("function", {}).get("name"),
        )
        if pending:
            # Quedan más escrituras propuestas en el mismo turno: confirmarlas
            # de una en una.
            conv.pending_tool_calls = json.dumps(pending)
            return self._confirm_payload(pending[0])
        conv.pending_tool_calls = False
        return self._run(conv)

    # ------------------------------------------------------------------
    # Bucle de tool-calling
    # ------------------------------------------------------------------
    def _run(self, conv):
        tools_model = self.env["odoo.ai.tools"]
        schemas = self._select_schemas(conv)
        max_iter = int(self._config("odoo_ai.max_tool_iterations"))

        for _i in range(max_iter):
            messages = self._build_messages(conv)
            try:
                assistant = self._call_llm(messages, schemas)
            except requests.RequestException as e:
                _logger.exception("vLLM request failed")
                msg = ("No he podido contactar con el modelo de IA. "
                       "Inténtalo de nuevo en unos segundos.")
                conv._add_message("assistant", content=msg)
                return {"type": "reply", "content": msg, "error": str(e)}

            tool_calls = assistant.get("tool_calls") or []
            content = assistant.get("content") or ""

            if not tool_calls:
                conv._add_message("assistant", content=content)
                return {"type": "reply", "content": content}

            # Persistimos el mensaje 'assistant' con sus tool_calls ANTES de
            # las respuestas 'tool' (lo exige el formato OpenAI).
            conv._add_message("assistant", content=content,
                              tool_calls=json.dumps(tool_calls))

            # 1ª pasada: ejecutar todas las herramientas de LECTURA.
            writes = []
            for tc in tool_calls:
                name = tc.get("function", {}).get("name")
                if tools_model.is_write_tool(name):
                    writes.append(tc)
                    continue
                result = self._resolve_tool_call(tc, confirm=True)
                conv._add_message("tool", content=result,
                                  tool_call_id=tc.get("id"), name=name)

            # 2ª: si hay escrituras, pausar y pedir confirmación al usuario.
            if writes:
                conv.pending_tool_calls = json.dumps(writes)
                return self._confirm_payload(writes[0])
            # Solo lecturas => seguimos el bucle (nueva llamada al LLM con los
            # resultados ya añadidos al historial).

        return {"type": "reply",
                "content": "He alcanzado el límite de pasos. "
                           "¿Puedes reformular la petición?"}

    # ------------------------------------------------------------------
    # Selección dinámica de tools (Fase 0.2)
    # ------------------------------------------------------------------
    def _enabled_packs(self):
        """Packs habilitados por configuración, intersecados con los
        realmente disponibles (módulos instalados)."""
        available = list(self.env["odoo.ai.tools"].list_packs())
        raw = (self._config("odoo_ai.enabled_packs") or "all").strip().lower()
        if raw in ("", "all", "*"):
            return available
        wanted = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        enabled = [p for p in available if p in wanted]
        # Config inválida (ningún pack reconocido) => no dejar al agente mudo.
        return enabled or available

    def _select_schemas(self, conv):
        """Decide qué schemas exponer al LLM en este turno.

        Con pocos packs/tools se exponen todos los habilitados; por encima del
        umbral, una primera llamada barata SIN tools clasifica la intención en
        packs y solo se exponen esos (los modelos pequeños degradan la elección
        de tool con catálogos grandes).
        """
        tools_model = self.env["odoo.ai.tools"]
        enabled = self._enabled_packs()
        schemas = tools_model.get_tool_schemas(packs=enabled)
        threshold = int(self._config("odoo_ai.router_threshold"))
        if len(schemas) <= threshold or len(enabled) <= 1:
            return schemas
        routed = self._route_packs(conv, enabled)
        if set(routed) == set(enabled):
            return schemas
        _logger.info("Router de packs: %s -> %s", enabled, routed)
        return tools_model.get_tool_schemas(packs=routed)

    def _route_packs(self, conv, enabled):
        """Clasifica el último mensaje del usuario en packs. Fallback: todos."""
        user_msgs = conv.message_ids.filtered(lambda m: m.role == "user")
        last = user_msgs[-1].content if user_msgs else ""
        if not last:
            return enabled
        pack_info = self.env["odoo.ai.tools"].list_packs()
        catalog = "\n".join(
            f"- {p}: {pack_info[p]}" for p in enabled if p in pack_info)
        router_messages = [
            {"role": "system", "content": (
                "Clasifica la petición del usuario en uno o más dominios del "
                f"ERP.\nDominios disponibles:\n{catalog}\n"
                "Responde SOLO con los nombres de los dominios relevantes "
                "separados por comas (p. ej. crm,sale), o all si no está "
                "claro. Nada más.")},
            {"role": "user", "content": last},
        ]
        try:
            msg = self._call_llm(router_messages, tools=None)
        except requests.RequestException:
            _logger.warning("Router de packs: fallo de LLM, expongo todos")
            return enabled
        tokens = re.split(r"[^a-z_]+", (msg.get("content") or "").lower())
        if "all" in tokens:
            return enabled
        chosen = [p for p in enabled if p in tokens]
        return chosen or enabled

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_tool_call(self, tc, confirm):
        fn = tc.get("function", {})
        name = fn.get("name")
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except (ValueError, TypeError):
            args = {}
        if not confirm:
            return "El usuario ha cancelado esta acción; no se ha ejecutado."
        return self.env["odoo.ai.tools"].execute_tool(name, args)

    def _cancel_pending(self, conv):
        pending = json.loads(conv.pending_tool_calls or "[]")
        for tc in pending:
            conv._add_message(
                "tool",
                content="El usuario no confirmó esta acción.",
                tool_call_id=tc.get("id"),
                name=tc.get("function", {}).get("name"),
            )
        if pending:
            conv.pending_tool_calls = False

    def _confirm_payload(self, tc):
        fn = tc.get("function", {})
        name = fn.get("name")
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except (ValueError, TypeError):
            args = {}
        return {
            "type": "confirm",
            "tool_name": name,
            "arguments": args,
            "description": self.env["odoo.ai.tools"].describe_action(name, args),
        }

    def _build_messages(self, conv):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in conv.message_ids:
            if m.role == "user":
                messages.append({"role": "user", "content": m.content or ""})
            elif m.role == "assistant":
                msg = {"role": "assistant", "content": m.content or ""}
                if m.tool_calls:
                    try:
                        msg["tool_calls"] = json.loads(m.tool_calls)
                    except (ValueError, TypeError):
                        pass
                messages.append(msg)
            elif m.role == "tool":
                messages.append({
                    "role": "tool",
                    "tool_call_id": m.tool_call_id or "",
                    "content": m.content or "",
                })
        return messages

    def _call_llm(self, messages, tools):
        base = self._config("odoo_ai.vllm_url").rstrip("/")
        payload = {
            "model": self._config("odoo_ai.model"),
            "messages": messages,
            "temperature": float(self._config("odoo_ai.temperature")),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        resp = requests.post(
            base + "/chat/completions",
            json=payload,
            timeout=float(self._config("odoo_ai.request_timeout")),
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            # Un 200 con un cuerpo inesperado (choices vacío, etc.) no debe
            # propagarse como un 500 crudo al RPC.
            _logger.error("Respuesta inesperada de vLLM: %s", data)
            raise requests.RequestException(
                "Respuesta inesperada del modelo de IA.") from e

    def _config(self, key):
        icp = self.env["ir.config_parameter"].sudo()
        return icp.get_param(key, DEFAULTS.get(key, ""))
