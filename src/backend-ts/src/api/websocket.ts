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

        const ctx = getContext();
        let currentPhase = "waiting_input";

        if (ctx.gmAgent) {
          const gameState = ctx.gmAgent.getGameState();
          if (gameState.session_id === sessionId) {
            currentPhase = gameState.current_phase;
          }
        }

        // Send initial status with ACTUAL phase, not "connected"
        manager.sendStatus(sessionId, currentPhase, "WebSocket connected");

        if (ctx.gmAgent) {
          const gameState = ctx.gmAgent.getGameState();
          if (gameState.session_id === sessionId) {
            // Push current phase explicitly as phase message too
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
          const rawData = evt.data.toString();
          console.log(`[WebSocket] Received raw message: ${rawData}`);
          
          const data = JSON.parse(rawData);
          const messageType = data.type as string;
          console.log(`[WebSocket] Parsed message type: ${messageType}`);

          // Support both legacy "player_action" and current frontend "player_input"
          if (messageType === "player_action" || messageType === "player_input") {
            let playerInput = "";
            let lang: "cn" | "en" = "cn";

            // Handle different data structures
            if (data.data && typeof data.data === 'object') {
                // Structure: { type: "player_action", data: { action: "...", lang: "..." } }
                playerInput = data.data.action || data.data.content;
                lang = data.data.lang || "cn";
            } else {
                // Structure: { type: "player_input", content: "...", lang: "..." }
                playerInput = data.content || data.action;
                lang = data.lang || "cn";
            }

            console.log(`[WebSocket] Player input extracted: ${playerInput}`);
            
            if (!playerInput) {
                console.warn("[WebSocket] Received empty player input");
                return;
            }

            const ctx = getContext();
            if (!ctx.gmAgent) {
              console.error("[WebSocket] GM Agent not initialized!");
              manager.sendError(sessionId, "Game engine not initialized");
              return;
            }

            // Set up status callback to notify frontend which agent is working (aligned with Python backend)
            ctx.gmAgent.setStatusCallback(async (agent: string, message: string | null) => {
              manager.sendStatus(sessionId, "processing", message || undefined, agent);
            });

            manager.sendStatus(sessionId, "processing", "analyzing_action", "gm");

            let response;
            try {
              response = await ctx.gmAgent.process({
                player_input: playerInput,
                lang,
              });
            } finally {
              // Clear callback after processing (aligned with Python backend)
              ctx.gmAgent.setStatusCallback(undefined as any);
            }
            console.log(`[WebSocket] GM Process result success: ${response.success}`);

            if (response.success) {
              // Send current phase after processing (aligned with Python backend)
              const gameStateAfterProcess = ctx.gmAgent.getGameState();
              manager.sendPhaseChange(sessionId, gameStateAfterProcess.current_phase);

              // Check for dice requirement BEFORE streaming/completing
              if (response.metadata?.requires_dice) {
                // Stream the narrative prompt (if any)
                if (response.content) {
                  // Send narrating status before streaming (aligned with Python backend)
                  manager.sendStatus(sessionId, "narrating", "generating_narrative");
                  await streamContent(sessionId, response.content);
                  manager.sendComplete(sessionId, response.content, response.metadata || {});
                }
                
                // Change phase to dice_check (send again to ensure frontend receives it)
                const gameState = ctx.gmAgent.getGameState();
                manager.sendPhaseChange(sessionId, gameState.current_phase);
                
                // Send dice check request (this keeps the turn active)
                manager.sendDiceCheck(
                  sessionId,
                  response.metadata.check_request as Record<string, unknown>
                );
                
                // DO NOT send phase back to waiting_input - stay in dice_check
                return;
              }
              
              // Normal response without dice check
              // Send narrating status before streaming (aligned with Python backend)
              manager.sendStatus(sessionId, "narrating", "generating_narrative");
              await streamContent(sessionId, response.content);
              manager.sendComplete(sessionId, response.content, response.metadata || {});
              
              // Ensure phase is synced after response
              const gameState = ctx.gmAgent.getGameState();
              manager.sendPhaseChange(sessionId, gameState.current_phase);
            } else {
              manager.sendError(sessionId, response.error || "Unknown error");
            }
          } else if (messageType === "dice_result") {
            // 前端直接在顶层发送字段，不是嵌套在 data 中
            const diceResult = {
              total: data.total as number,
              all_rolls: data.all_rolls as number[],
              kept_rolls: data.kept_rolls as number[],
              outcome: data.outcome as string,
              fate_point_spent: (data.fate_point_spent as boolean) ?? false,
            };
            const lang = (data.lang as "cn" | "en") || "cn";

            console.log(`[WebSocket] Dice result: total=${diceResult.total}, outcome=${diceResult.outcome}`);

            const ctx = getContext();
            if (!ctx.gmAgent) {
              manager.sendError(sessionId, "Game engine not initialized");
              return;
            }

            // Set up status callback to notify frontend which agent is working (aligned with Python backend)
            ctx.gmAgent.setStatusCallback(async (agent: string, message: string | null) => {
              manager.sendStatus(sessionId, "processing", message || undefined, agent);
            });

            manager.sendStatus(sessionId, "processing", "processing_dice_result", "gm");
            // Send processing phase (aligned with Python backend)
            manager.sendPhaseChange(sessionId, "processing");

            let response;
            try {
              response = await ctx.gmAgent.resumeAfterDice(diceResult, lang);
            } finally {
              // Clear callback after processing (aligned with Python backend)
              ctx.gmAgent.setStatusCallback(undefined as any);
            }

            if (response.success) {
              // Send current phase after processing (aligned with Python backend)
              const gameStateAfterProcess = ctx.gmAgent.getGameState();
              manager.sendPhaseChange(sessionId, gameStateAfterProcess.current_phase);

              if (response.metadata?.requires_dice) {
                if (response.content) {
                  // Send narrating status before streaming (aligned with Python backend)
                  manager.sendStatus(sessionId, "narrating", "generating_narrative");
                  await streamContent(sessionId, response.content);
                  manager.sendComplete(sessionId, response.content, response.metadata || {});
                }
                
                // Change phase to dice_check (send again to ensure frontend receives it)
                const gameState = ctx.gmAgent.getGameState();
                manager.sendPhaseChange(sessionId, gameState.current_phase);
                
                manager.sendDiceCheck(
                  sessionId,
                  response.metadata.check_request as Record<string, unknown>
                );
                
                return;
              }
              
              // Send narrating status before streaming (aligned with Python backend)
              manager.sendStatus(sessionId, "narrating", "generating_narrative");
              await streamContent(sessionId, response.content);
              manager.sendComplete(sessionId, response.content, response.metadata || {});
              
              const gameState = ctx.gmAgent.getGameState();
              manager.sendPhaseChange(sessionId, gameState.current_phase);
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
