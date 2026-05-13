import { Session, Message, Source, LLMConfig } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function chatBody(sessionId: string, message: string, llmConfig?: LLMConfig | null) {
  const body: Record<string, string | number> = { session_id: sessionId, message };
  if (llmConfig?.apiKey) {
    body.api_key = llmConfig.apiKey;
    if (llmConfig.baseUrl) body.base_url = llmConfig.baseUrl;
    if (llmConfig.model) body.model = llmConfig.model;
    if (llmConfig.temperature !== undefined) body.temperature = llmConfig.temperature;
    if (llmConfig.maxTokens !== undefined) body.max_tokens = llmConfig.maxTokens;
    if (llmConfig.topP !== undefined) body.top_p = llmConfig.topP;
  }
  return body;
}

export async function createSession(title: string = "新对话"): Promise<Session> {
  const res = await fetch(`${BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${BASE}/api/sessions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`${BASE}/api/sessions/${id}`, { method: "DELETE" });
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const res = await fetch(`${BASE}/api/sessions/${sessionId}/messages`);
  if (!res.ok) return [];
  return res.json();
}

export function streamChat(
  sessionId: string,
  message: string,
  onToken: (token: string) => void,
  onSources: (sources: Source[]) => void,
  onDone: () => void,
  onError: (err: string) => void,
  llmConfig?: LLMConfig | null,
): AbortController {
  const controller = new AbortController();

  fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chatBody(sessionId, message, llmConfig)),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        onError(`HTTP ${res.status}`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === "token") {
                onToken(data.content);
              } else if (data.type === "sources") {
                onSources(data.sources);
              } else if (data.type === "done") {
                onDone();
              }
            } catch {
              // skip malformed
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(err.message);
    });

  return controller;
}

export async function stopChat(sessionId: string): Promise<void> {
  await fetch(`${BASE}/api/chat/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}
