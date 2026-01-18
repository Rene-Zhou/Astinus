import type { UpgradeWebSocket, WSContext } from "hono/ws";
import type { AppContext } from "../index";

export enum MessageType {
  STATUS = "status",
  CONTENT = "content",
  COMPLETE = "complete",
  ERROR = "error",
  PHASE = "phase",
  DICE_CHECK = "dice_check",
  DICE_RESULT = "dice_result",
}

interface StreamMessage {
  type: MessageType;
  data: Record<string, unknown>;
}

class ConnectionManager {
  private connections: Map<string, WSContext> = new Map();

  connect(sessionId: string, ws: WSContext): void {
    this.connections.set(sessionId, ws);
  }

  disconnect(sessionId: string): void {
    this.connections.delete(sessionId);
  }

  sendMessage(sessionId: string, message: StreamMessage): void {
    const ws = this.connections.get(sessionId);
    if (ws) {
      ws.send(JSON.stringify(message));
    }
  }

  sendStatus(
    sessionId: string,
    phase: string,
    message?: string,
    agent?: string
  ): void {
    const data: Record<string, unknown> = { phase, message: message || "" };
    if (agent) {
      data.agent = agent;
    }
    this.sendMessage(sessionId, {
      type: MessageType.STATUS,
      data,
    });
  }

  sendContentChunk(
    sessionId: string,
    chunk: string,
    isPartial: boolean = true,
    chunkIndex: number = 0
  ): void {
    this.sendMessage(sessionId, {
      type: MessageType.CONTENT,
      data: {
        chunk,
        is_partial: isPartial,
        chunk_index: chunkIndex,
      },
    });
  }

  sendComplete(
    sessionId: string,
    content: string,
    metadata: Record<string, unknown>,
    success: boolean = true
  ): void {
    this.sendMessage(sessionId, {
      type: MessageType.COMPLETE,
      data: {
        content,
        metadata,
        success,
      },
    });
  }

  sendError(sessionId: string, error: string): void {
    this.sendMessage(sessionId, {
      type: MessageType.ERROR,
      data: { error },
    });
  }

  sendPhaseChange(sessionId: string, phase: string): void {
    this.sendMessage(sessionId, {
      type: MessageType.PHASE,
      data: { phase },
    });
  }

  sendDiceCheck(
    sessionId: string,
    checkRequest: Record<string, unknown>
  ): void {
    this.sendMessage(sessionId, {
      type: MessageType.DICE_CHECK,
      data: { check_request: checkRequest },
    });
  }
}

const manager = new ConnectionManager();

async function streamContent(
  sessionId: string,
  content: string,
  chunkSize: number = 20,
  delay: number = 30
): Promise<void> {
  for (let i = 0; i < content.length; i += chunkSize) {
    const chunk = content.slice(i, i + chunkSize);
    const isPartial = i + chunkSize < content.length;
    manager.sendContentChunk(sessionId, chunk, isPartial, Math.floor(i / chunkSize));
    if (isPartial) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
}

export function createWebSocketHandler(
  upgradeWebSocket: UpgradeWebSocket,
  getContext: () => AppContext
) {
  return upgradeWebSocket((c) => {
    const sessionId = c.req.param("sessionId");

    return {
      onOpen(_evt, ws) {
        console.log(`[WebSocket] Client connected: ${sessionId}`);
        manager.connect(sessionId, ws);
        manager.sendStatus(sessionId, "connected", "WebSocket connected");

        const ctx = getContext();
        if (ctx.gmAgent) {
          const gameState = ctx.gmAgent.getGameState();
          if (gameState.session_id === sessionId) {
            // Push current phase
            manager.sendPhaseChange(sessionId, gameState.current_phase);

            // Push last message if any
            if (gameState.messages.length > 0) {
              const lastMsg = gameState.messages[gameState.messages.length - 1];
              if (lastMsg) {
                manager.sendComplete(
                  sessionId,
                  lastMsg.content,
                  lastMsg.metadata || {},
                  true
                );
              }
            }
          }
        }
      },

      async onMessage(evt, ws) {
        try {
          const data = JSON.parse(evt.data.toString());
          const messageType = data.type as string;

          if (messageType === "player_action") {
            const playerInput = data.data.action as string;
            const lang = (data.data.lang as "cn" | "en") || "cn";

            const ctx = getContext();
            if (!ctx.gmAgent) {
              manager.sendError(sessionId, "Game engine not initialized");
              return;
            }

            manager.sendStatus(sessionId, "processing", "Processing action...");

            const response = await ctx.gmAgent.process({
              player_input: playerInput,
              lang,
            });

            if (response.success) {
              await streamContent(sessionId, response.content);
              manager.sendComplete(sessionId, response.content, response.metadata || {});

              if (response.metadata?.requires_dice) {
                manager.sendDiceCheck(
                  sessionId,
                  response.metadata.check_request as Record<string, unknown>
                );
              }
            } else {
              manager.sendError(sessionId, response.error || "Unknown error");
            }
          } else if (messageType === "dice_result") {
            const diceResult = data.data as Record<string, unknown>;
            const lang = (data.lang as "cn" | "en") || "cn";

            const ctx = getContext();
            if (!ctx.gmAgent) {
              manager.sendError(sessionId, "Game engine not initialized");
              return;
            }

            manager.sendStatus(sessionId, "processing", "Processing dice result...");

            const response = await ctx.gmAgent.resumeAfterDice(diceResult, lang);

            if (response.success) {
              await streamContent(sessionId, response.content);
              manager.sendComplete(sessionId, response.content, response.metadata || {});
            } else {
              manager.sendError(sessionId, response.error || "Unknown error");
            }
          } else if (messageType === "ping") {
            ws.send(JSON.stringify({ type: "pong" }));
          }
        } catch (error) {
          console.error(`[WebSocket] Error processing message:`, error);
          manager.sendError(
            sessionId,
            `Error: ${error instanceof Error ? error.message : String(error)}`
          );
        }
      },

      onClose(_evt, _ws) {
        console.log(`[WebSocket] Client disconnected: ${sessionId}`);
        manager.disconnect(sessionId);
      },

      onError(_evt, _ws) {
        console.error(`[WebSocket] Error for ${sessionId}:`, _evt);
        manager.disconnect(sessionId);
      },
    };
  });
}

export { manager, streamContent };
