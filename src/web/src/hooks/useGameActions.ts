import { useCallback, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { DiceOutcome, DiceResult, GameState, Message } from "../api/types";
import { useGameStore } from "../stores/gameStore";

/**
 * Hook bundling common game actions (REST + WS) and a minimal dice roller utility.
 *
 * - Uses REST endpoints for initial state/messages.
 * - Delegates live interaction to Zustand gameStore (which wraps WebSocket client).
 * - Provides a basic dice roller (supports "XdY" format).
 */
export function useGameActions() {
  const {
    startNewGame,
    sendPlayerInput,
    submitDiceResult: submitDiceResultWs,
    hydrateGameState,
    setMessages,
  } = useGameStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshState = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.getGameState();
    setLoading(false);

    if (!res.data) {
      setError(res.error ?? "Failed to fetch game state");
      return;
    }
    hydrateGameState(res.data as GameState);
  }, [hydrateGameState]);

  const fetchMessages = useCallback(
    async (options?: { limit?: number; offset?: number }) => {
      setError(null);
      const res = await apiClient.getMessages({
        limit: options?.limit,
        offset: options?.offset,
      });
      if (!res.data) {
        setError(res.error ?? "Failed to fetch messages");
        return;
      }
      setMessages(res.data.messages as Message[]);
    },
    [setMessages],
  );

  const createNewGame = useCallback(
    async (opts?: { worldPackId?: string; playerName?: string }) => {
      setLoading(true);
      setError(null);
      try {
        await startNewGame(opts);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Failed to start new game";
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [startNewGame],
  );

  const sendAction = useCallback(
    (content: string, lang: "cn" | "en" = "cn") => {
      sendPlayerInput(content, lang);
    },
    [sendPlayerInput],
  );

  const submitDiceResult = useCallback(
    (result: DiceResult) => {
      submitDiceResultWs(result);
    },
    [submitDiceResultWs],
  );

  /**
   * Minimal dice roller supporting "XdY" expressions.
   * Falls back to 1d6 when parsing fails.
   */
  const rollDice = useCallback((formula?: string): DiceResult => {
    const parsed = parseDiceFormula(formula);
    const rolls: number[] = [];
    for (let i = 0; i < parsed.count; i += 1) {
      rolls.push(1 + Math.floor(Math.random() * parsed.sides));
    }
    const total = rolls.reduce((acc, n) => acc + n, 0);
    const outcome: DiceOutcome =
      total >= parsed.count * (parsed.sides / 2) ? "success" : "failure";
    return {
      total,
      all_rolls: rolls,
      kept_rolls: rolls,
      outcome,
    };
  }, []);

  return useMemo(
    () => ({
      loading,
      error,
      createNewGame,
      sendAction,
      refreshState,
      fetchMessages,
      submitDiceResult,
      rollDice,
    }),
    [
      loading,
      error,
      createNewGame,
      sendAction,
      refreshState,
      fetchMessages,
      submitDiceResult,
      rollDice,
    ],
  );
}

function parseDiceFormula(formula?: string): { count: number; sides: number } {
  if (!formula) return { count: 1, sides: 6 };
  const match = formula.trim().match(/^(\d+)d(\d+)$/i);
  if (!match) return { count: 1, sides: 6 };
  const count = Number(match[1]);
  const sides = Number(match[2]);
  if (Number.isNaN(count) || Number.isNaN(sides) || count <= 0 || sides <= 1) {
    return { count: 1, sides: 6 };
  }
  return { count, sides };
}
