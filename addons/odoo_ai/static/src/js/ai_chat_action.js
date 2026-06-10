/** @odoo-module **/

import { Component, useState, onWillStart, onPatched, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const POLL_INTERVAL_MS = 1500;

export class AiChatAction extends Component {
    static template = "odoo_ai.ChatAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            messages: [], // {role: 'user'|'assistant', content}
            input: "",
            loading: false,
            thinking: false, // modo asíncrono: job en proceso (Fase 0.3)
            pending: null, // {tool_name, arguments, description}
        });
        this.threadRef = useRef("thread");
        this.pollTimer = null;

        onWillStart(async () => {
            const ids = await this.orm.create("odoo.ai.conversation", [
                { name: "Asistente IA" },
            ]);
            this.conversationId = ids[0];
        });
        onPatched(() => this._scrollToBottom());
        onWillUnmount(() => this._stopPolling());
    }

    _scrollToBottom() {
        const el = this.threadRef.el;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }

    _push(role, content) {
        this.state.messages.push({ role, content });
    }

    _stopPolling() {
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
    }

    _handle(res) {
        if (!res) {
            return;
        }
        if (res.type === "queued") {
            // Modo asíncrono: el turno corre en un job; recogemos por polling.
            this._poll(res.last_message_id || 0);
            return;
        }
        if (res.type === "confirm") {
            this.state.pending = {
                tool_name: res.tool_name,
                arguments: res.arguments,
                description: res.description,
            };
        } else {
            this.state.pending = null;
            if (res.content) {
                this._push("assistant", res.content);
            }
        }
    }

    async _poll(lastId) {
        this.state.thinking = true;
        let res;
        try {
            res = await this.orm.call("odoo.ai.conversation", "poll_updates", [
                [this.conversationId],
                lastId,
            ]);
        } catch {
            // Error transitorio de red: reintenta en el siguiente tick.
            this.pollTimer = setTimeout(() => this._poll(lastId), POLL_INTERVAL_MS);
            return;
        }
        for (const m of res.messages) {
            this._push("assistant", m.content);
        }
        if (res.thinking) {
            this.pollTimer = setTimeout(
                () => this._poll(res.last_message_id), POLL_INTERVAL_MS);
            return;
        }
        this.state.thinking = false;
        this.state.pending = res.pending || null;
    }

    get busy() {
        return this.state.loading || this.state.thinking;
    }

    async sendMessage() {
        const text = this.state.input.trim();
        if (!text || this.busy || this.state.pending) {
            return;
        }
        this._push("user", text);
        this.state.input = "";
        this.state.loading = true;
        try {
            const res = await this.orm.call("odoo.ai.conversation", "chat", [
                [this.conversationId],
                text,
            ]);
            this._handle(res);
        } finally {
            this.state.loading = false;
        }
    }

    async confirm(ok) {
        if (this.busy || !this.state.pending) {
            return;
        }
        const pending = this.state.pending;
        this.state.pending = null;
        this._push("assistant", `${ok ? "✅ Confirmado" : "❌ Cancelado"}: ${pending.description}`);
        this.state.loading = true;
        try {
            const res = await this.orm.call("odoo.ai.conversation", "execute_pending", [
                [this.conversationId],
                ok,
            ]);
            this._handle(res);
        } finally {
            this.state.loading = false;
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }
}

registry.category("actions").add("odoo_ai.ChatAction", AiChatAction);
