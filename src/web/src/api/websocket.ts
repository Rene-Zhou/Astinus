import type {
  ConnectionStatus,
  DiceOutcome,
  DiceResult,
  DiceResultRequest,
  Language,
  WSDiceCheckMessage,
  WSCompleteMessage,
  WSContentMessage,
  WSErrorMessage,
  WSPhaseMessage,
  WSStatusMessage,
} from "./types";

type ServerMessage =
  | WSStatusMessage
  | WSContentMessage
  | WSCompleteMessage
  | WSDiceCheckMessage
  | WSPhaseMessage
  | WSErrorMessage;

export interface GameWebSocketOptions {
  sessionId: string;
  /**
   * Optional absolute WebSocket base URL (e.g. ws://localhost:8000).
   * If not provided, it will be derived from window.location.
   */
  baseUrl?: string;
  reconnect?: {
    enabled?: boolean;
    maxAttempts?: number;
    initialDelayMs?: number;
    maxDelayMs?: number;
  };
  handlers?: Partial<GameWebSocketEventHandlers>;
}

export interface GameWebSocketEventHandlers {
  onOpen: (event: Event) => void;
  onClose: (event: CloseEvent) => void;
  onError: (event: Event) => void;
  onStatus: (message: WSStatusMessage) => void;
  onContent: (message: WSContentMessage) => void;
  onComplete: (message: WSCompleteMessage) => void;
  onDiceCheck: (message: WSDiceCheckMessage) => void;
  onPhase: (message: WSPhaseMessage) => void;
  onServerError: (message: WSErrorMessage) => void;
  onMessageUnknown: (event: MessageEvent) => void;
}

const defaultHandlers: GameWebSocketEventHandlers = {
  onOpen: () => {},
  onClose: () => {},
  onError: () => {},
  onStatus: () => {},
  onContent: () => {},
  onComplete: () => {},
  onDiceCheck: () => {},
  onPhase: () => {},
  onServerError: () => {},
  onMessageUnknown: () => {},
};

export class GameWebSocketClient {
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = "disconnected";
  private reconnectAttempts = 0;
  private closedManually = false;
  private readonly opts: GameWebSocketOptions;
  private readonly handlers: GameWebSocketEventHandlers;

  constructor(options: GameWebSocketOptions) {
    this.opts = options;
    this.handlers = { ...defaultHandlers, ...(options.handlers ?? {}) };
  }

  get connectionStatus(): ConnectionStatus {
    return this.status;
  }

  connect(): void {
    if (
      this.ws &&
      (this.status === "connected" || this.status === "connecting")
    ) {
      return;
    }

    this.closedManually = false;
    this.setStatus("connecting");
    const url = this.buildWsUrl(this.opts.sessionId, this.opts.baseUrl);
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = (event) => {
      this.reconnectAttempts = 0;
      this.setStatus("connected");
      this.handlers.onOpen(event);
    };

    ws.onclose = (event) => {
      this.setStatus("disconnected");
      this.handlers.onClose(event);
      if (!this.closedManually) {
        this.scheduleReconnect();
      }
    };

    ws.onerror = (event) => {
      this.setStatus("error");
      this.handlers.onError(event);
    };

    ws.onmessage = (event) => {
      this.handleMessage(event);
    };
  }

  disconnect(code?: number, reason?: string): void {
    this.closedManually = true;
    if (this.ws && this.status !== "disconnected") {
      this.ws.close(code, reason);
    }
    this.ws = null;
    this.setStatus("disconnected");
  }

  sendPlayerInput(content: string, lang: Language = "cn", stream = true): void {
    if (!this.ws || this.status !== "connected") return;
    this.ws.send(
      JSON.stringify({
        type: "player_input",
        content,
        lang,
        stream,
      }),
    );
  }

  sendDiceResult(result: DiceResult): void {
    if (!this.ws || this.status !== "connected") return;
    const payload: DiceResultRequest & {
      type: "dice_result";
      outcome: DiceOutcome;
    } = {
      type: "dice_result",
      total: result.total,
      all_rolls: result.all_rolls,
      kept_rolls: result.kept_rolls,
      outcome: result.outcome,
      fate_point_spent: result.fate_point_spent ?? false,
    };
    this.ws.send(JSON.stringify(payload));
  }

  private handleMessage(event: MessageEvent): void {
    let parsed: ServerMessage | null = null;
    try {
      parsed = JSON.parse(event.data as string) as ServerMessage;
    } catch {
      this.handlers.onMessageUnknown(event);
      return;
    }

    switch (parsed.type) {
      case "status":
        this.handlers.onStatus(parsed);
        break;
      case "content":
        this.handlers.onContent(parsed);
        break;
      case "complete":
        this.handlers.onComplete(parsed);
        break;
      case "dice_check":
        this.handlers.onDiceCheck(parsed);
        break;
      case "phase":
        this.handlers.onPhase(parsed);
        break;
      case "error":
        this.handlers.onServerError(parsed);
        break;
      default:
        this.handlers.onMessageUnknown(event);
    }
  }

  private scheduleReconnect(): void {
    const { reconnect } = this.opts;
    if (!reconnect?.enabled) return;

    const maxAttempts = reconnect.maxAttempts ?? 5;
    if (this.reconnectAttempts >= maxAttempts) return;

    this.reconnectAttempts += 1;
    this.setStatus("reconnecting");

    const initial = reconnect.initialDelayMs ?? 500;
    const max = reconnect.maxDelayMs ?? 5_000;
    const delay = Math.min(
      max,
      initial * Math.pow(2, this.reconnectAttempts - 1),
    );

    window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  private buildWsUrl(sessionId: string, baseUrl?: string): string {
    if (baseUrl) {
      const normalized = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
      return `${normalized}/ws/game/${sessionId}`;
    }

    const { protocol, host } = window.location;
    const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${host}/ws/game/${sessionId}`;
  }

  private setStatus(status: ConnectionStatus): void {
    this.status = status;
  }
}
