import type {
  ActionRequest,
  ActionResponse,
  DiceResultRequest,
  DiceResultResponse,
  GetGameStateResponse,
  GetMessagesResponse,
  HealthResponse,
  NewGameRequest,
  NewGameResponse,
  ResetResponse,
  RootResponse,
  WorldPackDetailResponse,
} from "./types";

/**
 * Minimal, typed REST client for the Astinus backend.
 * Uses fetch with JSON helpers and returns typed responses.
 */

type HttpMethod = "GET" | "POST";
type HeadersInit = Record<string, string>;

export interface RequestOptions<TBody = unknown> {
  path: string;
  method?: HttpMethod;
  body?: TBody;
  signal?: AbortSignal;
  headers?: HeadersInit;
}

export interface ApiResult<T> {
  data: T | null;
  error: string | null;
  status: number;
}

const API_BASE_URL =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE_URL) ??
  "";

const defaultHeaders: HeadersInit = {
  "Content-Type": "application/json",
};

async function request<TResponse, TBody = unknown>({
  path,
  method = "GET",
  body,
  signal,
  headers,
}: RequestOptions<TBody>): Promise<ApiResult<TResponse>> {
  const url = `${API_BASE_URL}${path}`;
  const init: RequestInit = {
    method,
    headers: {
      ...defaultHeaders,
      ...(headers ?? {}),
    },
    signal,
  };

  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  let status = 0;
  try {
    const res = await fetch(url, init);
    status = res.status;

    const isJson =
      res.headers.get("content-type")?.includes("application/json") ?? false;
    const parsed = isJson ? await res.json() : null;

    if (!res.ok) {
      const detail =
        (parsed as { detail?: string })?.detail ??
        (parsed as { error?: string })?.error ??
        res.statusText;
      return { data: null, error: detail ?? "Request failed", status };
    }

    return { data: parsed as TResponse, error: null, status };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Network or fetch error";
    return { data: null, error: message, status };
  }
}

/**
 * Query builders
 */
const withQuery = (
  path: string,
  query?: Record<string, string | number | undefined>,
) => {
  if (!query) return path;
  const params = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null) params.append(k, String(v));
  });
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
};

/**
 * API surface
 */
export const apiClient = {
  async getRoot(signal?: AbortSignal) {
    return request<RootResponse>({ path: "/", signal });
  },

  async getHealth(signal?: AbortSignal) {
    return request<HealthResponse>({ path: "/health", signal });
  },

  async createNewGame(body: NewGameRequest, signal?: AbortSignal) {
    return request<NewGameResponse>({
      path: "/api/v1/game/new",
      method: "POST",
      body,
      signal,
    });
  },

  async sendAction(body: ActionRequest, signal?: AbortSignal) {
    return request<ActionResponse>({
      path: "/api/v1/game/action",
      method: "POST",
      body,
      signal,
    });
  },

  async getGameState(signal?: AbortSignal) {
    return request<GetGameStateResponse>({
      path: "/api/v1/game/state",
      method: "GET",
      signal,
    });
  },

  async submitDiceResult(body: DiceResultRequest, signal?: AbortSignal) {
    return request<DiceResultResponse>({
      path: "/api/v1/game/dice-result",
      method: "POST",
      body,
      signal,
    });
  },

  async getMessages(options?: {
    limit?: number;
    offset?: number;
    signal?: AbortSignal;
  }) {
    const { limit, offset, signal } = options ?? {};
    const path = withQuery("/api/v1/game/messages", { limit, offset });
    return request<GetMessagesResponse>({ path, method: "GET", signal });
  },

  async resetGame(signal?: AbortSignal) {
    return request<ResetResponse>({
      path: "/api/v1/game/reset",
      method: "POST",
      signal,
    });
  },

  /**
   * Get world pack details including preset characters
   */
  async getWorldPackDetail(packId: string, signal?: AbortSignal) {
    return request<WorldPackDetailResponse>({
      path: `/api/v1/game/world-pack/${encodeURIComponent(packId)}`,
      method: "GET",
      signal,
    });
  },
};

export type ApiClient = typeof apiClient;
