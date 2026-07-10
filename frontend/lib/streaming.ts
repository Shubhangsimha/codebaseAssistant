export interface Citation {
  file: string;
  line_start: number;
  line_end: number;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onCitations: (citations: Citation[]) => void;
  onDone: (conversationId: number, messageId: number) => void;
  onError: (message: string) => void;
}

export async function streamChat(
  url: string,
  body: { message: string; conversation_id?: number },
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    let message = `HTTP ${res.status}`;
    try {
      const errBody = await res.json();
      message = errBody?.detail ?? errBody?.message ?? message;
    } catch {
      // ignore
    }
    callbacks.onError(message);
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
    // Keep the last (potentially incomplete) line in the buffer
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;

      let event: Record<string, unknown>;
      try {
        event = JSON.parse(raw);
      } catch {
        continue;
      }

      switch (event.type) {
        case "token":
          callbacks.onToken(event.content as string);
          break;
        case "citations":
          callbacks.onCitations(event.citations as Citation[]);
          break;
        case "done":
          callbacks.onDone(
            event.conversation_id as number,
            event.message_id as number
          );
          break;
        case "error":
          callbacks.onError(event.message as string);
          break;
      }
    }
  }
}
