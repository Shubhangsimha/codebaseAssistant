"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { Send, Plus, MessageSquare, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getConversations,
  getConversationMessages,
  getFileContent,
  getChatStreamUrl,
  type ConversationResponse,
} from "@/lib/api";
import { streamChat, type Citation } from "@/lib/streaming";
import { useProjectStore } from "@/lib/projectStore";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DisplayMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
  model_used?: string | null;
}

// ---------------------------------------------------------------------------
// Citation pill — clickable, opens CodeViewer at the cited lines
// ---------------------------------------------------------------------------

function CitationPill({
  citation,
  projectId,
}: {
  citation: Citation;
  projectId: number;
}) {
  const { setOpenFile, setHighlight, openFile } = useProjectStore();
  const label = `${citation.file.split("/").pop()}:${citation.line_start}–${citation.line_end}`;

  async function handleClick() {
    // If the file is already open, just jump to the line
    if (openFile?.path === citation.file) {
      setHighlight(citation.line_start, citation.line_end);
      return;
    }
    try {
      const res = await getFileContent(projectId, citation.file);
      setOpenFile({
        path: citation.file,
        content: res.content,
        language: res.language,
        line_count: res.line_count,
        highlightFrom: citation.line_start,
        highlightTo: citation.line_end,
      });
    } catch {
      toast.error(`Could not open ${citation.file}`);
    }
  }

  return (
    <button
      onClick={handleClick}
      title={`${citation.file} lines ${citation.line_start}–${citation.line_end}`}
      className="inline-block text-xs bg-accent text-accent-foreground hover:bg-accent/80 rounded px-1.5 py-0.5 mr-1 mt-1 font-mono cursor-pointer transition-colors"
    >
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({
  msg,
  projectId,
}: {
  msg: DisplayMessage;
  projectId: number;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-muted text-foreground rounded-bl-sm"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{msg.content}</p>

        {msg.streaming && (
          <span className="inline-block w-1.5 h-4 bg-current ml-0.5 animate-pulse rounded-sm align-bottom" />
        )}

        {msg.citations && msg.citations.length > 0 && (
          <div className="mt-2 pt-2 border-t border-current/10">
            <p className="text-xs opacity-60 mb-1">Sources</p>
            {msg.citations.map((c, i) => (
              <CitationPill key={i} citation={c} projectId={projectId} />
            ))}
          </div>
        )}

        {msg.model_used && !msg.streaming && (
          <p className="text-xs opacity-40 mt-1.5">via {msg.model_used}</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main chat page
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    loadConversations();
  }, [projectId]);

  async function loadConversations() {
    try {
      const convs = await getConversations(projectId);
      setConversations(convs);
    } catch {
      toast.error("Failed to load conversations.");
    }
  }

  async function selectConversation(convId: number) {
    if (streaming) return;
    setActiveConvId(convId);
    setLoadingHistory(true);
    try {
      const msgs = await getConversationMessages(projectId, convId);
      setMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          citations: m.citations ? JSON.parse(m.citations) : undefined,
          model_used: m.model_used,
        }))
      );
    } catch {
      toast.error("Failed to load conversation history.");
    } finally {
      setLoadingHistory(false);
    }
  }

  function startNewConversation() {
    if (streaming) return;
    setActiveConvId(null);
    setMessages([]);
    inputRef.current?.focus();
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || streaming) return;

    setInput("");
    setStreaming(true);

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", streaming: true },
    ]);

    abortRef.current = new AbortController();
    let accum = "";

    try {
      await streamChat(
        getChatStreamUrl(projectId),
        { message: text, conversation_id: activeConvId ?? undefined },
        {
          onToken: (token) => {
            accum += token;
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = { ...last, content: accum };
              }
              return next;
            });
          },
          onCitations: (citations) => {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = { ...last, citations };
              }
              return next;
            });
          },
          onDone: (convId, msgId) => {
            setActiveConvId(convId);
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = { ...last, id: msgId, streaming: false };
              }
              return next;
            });
            loadConversations();
          },
          onError: (msg) => {
            toast.error(msg || "AI temporarily unavailable. Retry in 30s.");
            setMessages((prev) => prev.slice(0, -1));
          },
        },
        abortRef.current.signal
      );
    } catch (err: unknown) {
      if ((err as { name?: string })?.name !== "AbortError") {
        toast.error("Connection error. Please retry.");
        setMessages((prev) => prev.slice(0, -1));
      }
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-full">
      {/* Conversation sidebar */}
      <aside className="w-52 border-r flex flex-col shrink-0">
        <div className="p-3 border-b">
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={startNewConversation}
            disabled={streaming}
          >
            <Plus size={14} />
            New Chat
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
          {conversations.length === 0 ? (
            <p className="text-xs text-muted-foreground px-2 py-3 text-center">
              No conversations yet
            </p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                disabled={streaming}
                className={`w-full text-left px-2 py-2 rounded-md text-xs leading-snug transition-colors flex items-start gap-2 ${
                  activeConvId === conv.id
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`}
              >
                <MessageSquare size={12} className="mt-0.5 shrink-0" />
                <span className="truncate">{conv.title ?? "Untitled"}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Messages area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto px-4 pt-6 pb-2">
          {loadingHistory ? (
            <div className="flex justify-center pt-20">
              <Loader2 className="animate-spin text-muted-foreground" size={20} />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center pb-16">
              <MessageSquare size={40} className="text-muted-foreground/30 mb-4" />
              <p className="text-lg font-semibold mb-1">Ask anything about this codebase</p>
              <p className="text-sm text-muted-foreground">
                Try: &quot;What does this project do?&quot; or &quot;How does authentication work?&quot;
              </p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} projectId={projectId} />
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t px-4 py-3 shrink-0">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about the codebase…"
              disabled={streaming}
              className="flex-1"
              autoFocus
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || streaming}
              size="icon"
            >
              {streaming ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
