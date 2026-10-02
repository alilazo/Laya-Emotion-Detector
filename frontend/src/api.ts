import type { Analytics, Chat, ChatEmotion, Mode } from "./types";

let accessKey = sessionStorage.getItem("localAccessKey") || "";
const urlKey = new URLSearchParams(location.search).get("key");
if (urlKey) {
  accessKey = urlKey;
  sessionStorage.setItem("localAccessKey", urlKey);
  history.replaceState(null, "", location.pathname);
}

export function hasAccessKey() {
  return !!accessKey;
}
export function setAccessKey(key: string) {
  accessKey = key.trim();
  sessionStorage.setItem("localAccessKey", accessKey);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessKey}`,
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export const api = {
  health: () =>
    fetch("/api/health").then((response) => response.json()) as Promise<{
      emotion: string;
      checkpoint: string;
      error: string | null;
      chat: string;
      chat_model: string;
    }>,
  chats: () => request<Chat[]>("/chats"),
  createChat: () =>
    request<Chat>("/chats", { method: "POST", body: JSON.stringify({}) }),
  chat: (id: string) => request<Chat>(`/chats/${id}`),
  deleteChat: (id: string) =>
    request<{ deleted: boolean }>(`/chats/${id}`, { method: "DELETE" }),
  send: (id: string, content: string) =>
    request<{
      emotionStatus: string;
      replyStatus: string;
      replyError: string | null;
      chat: Chat;
    }>(`/chats/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  chatEmotion: (id: string) => request<ChatEmotion>(`/chats/${id}/emotion`),
  analytics: (params: {
    mode: Mode;
    start_date?: string;
    end_date?: string;
    min_anxiety: number;
    min_sadness: number;
    min_fear: number;
    dominant: string;
    search: string;
  }) =>
    request<Analytics>(
      `/emotion/analytics?${new URLSearchParams(
        Object.entries(params)
          .filter(([, value]) => value !== undefined)
          .map(([key, value]) => [key, String(value)]),
      ).toString()}`,
    ),
};
