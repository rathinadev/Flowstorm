import type { WSMessage } from "../types/websocket";

type MessageHandler = (message: WSMessage) => void;

class FlowStormWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private globalHandlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pipelineId: string = "";
  private _connected = false;

  get connected() {
    return this._connected;
  }

  connect(pipelineId: string) {
    this.pipelineId = pipelineId;
    this.disconnect();

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/api/ws/pipeline/${pipelineId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this._connected = true;
      console.log(`[WS] Connected to pipeline ${pipelineId}`);
      // Subscribe to metrics
      this.send({ type: "subscribe_metrics" });
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.dispatch(message);
      } catch (e) {
        console.error("[WS] Parse error:", e);
      }
    };

    this.ws.onclose = () => {
      this._connected = false;
      console.log("[WS] Disconnected");
      // Auto-reconnect after 3 seconds
      this.reconnectTimer = setTimeout(() => {
        if (this.pipelineId) {
          console.log("[WS] Reconnecting...");
          this.connect(this.pipelineId);
        }
      }, 3000);
    };

    this.ws.onerror = (error) => {
      console.error("[WS] Error:", error);
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._connected = false;
  }

  send(data: Record<string, unknown>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
    return () => this.handlers.get(type)?.delete(handler);
  }

  onAny(handler: MessageHandler) {
    this.globalHandlers.add(handler);
    return () => this.globalHandlers.delete(handler);
  }

  private dispatch(message: WSMessage) {
    // Type-specific handlers
    const typeHandlers = this.handlers.get(message.type);
    if (typeHandlers) {
      typeHandlers.forEach((h) => h(message));
    }

    // Global handlers
    this.globalHandlers.forEach((h) => h(message));
  }
}

export const wsClient = new FlowStormWebSocket();
