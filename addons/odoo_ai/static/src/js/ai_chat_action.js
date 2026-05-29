/** @odoo-module **/

import { Component, useState, onWillStart, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AiChatAction extends Component {
    static template = "odoo_ai.ChatAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            messages: [], // {role: 'user'|'assistant', content}
            input: "",
            loading: false,
            pending: null, // {tool_name, arguments, description}
        });
        this.threadRef = useRef("thread");

        onWillStart(async () => {
            const ids = await this.orm.create("odoo.ai.conversation", [
                { name: "Asistente IA" },
            ]);
            this.conversationId = ids[0];
        });
        onPatched(() => this._scrollToBottom());
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

    _handle(res) {
        if (!res) {
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

    async sendMessage() {
        const text = this.state.input.trim();
        if (!text || this.state.loading || this.state.pending) {
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
        if (this.state.loading || !this.state.pending) {
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
