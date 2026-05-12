"use client";
import { useState, useRef, useCallback } from "react";
import { Message, Source } from "@/lib/types";
import * as api from "@/lib/api";

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingSources, setStreamingSources] = useState<Source[]>([]);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(async () => {
    if (!sessionId) { setMessages([]); return; }
    try {
      const msgs = await api.getMessages(sessionId);
      setMessages(msgs);
    } catch { setMessages([]); }
  }, [sessionId]);

  const send = useCallback(async (content: string) => {
    if (!sessionId || !content.trim() || streaming) return;
    setError(null);
    setStreaming(true);
    setStreamingContent("");
    setStreamingSources([]);

    const userMsg: Message = {
      id: Date.now(), session_id: sessionId, role: "user",
      content, sources: [], created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    let finalContent = "";
    abortRef.current = api.streamChat(
      sessionId, content,
      (token) => { finalContent += token; setStreamingContent(finalContent); },
      (sources) => setStreamingSources(sources),
      () => {
        const aiMsg: Message = {
          id: Date.now() + 1, session_id: sessionId, role: "assistant",
          content: finalContent, sources: [], created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
        setStreaming(false);
        setStreamingContent("");
      },
      (err) => { setError(err); setStreaming(false); },
    );
  }, [sessionId, streaming]);

  const stop = useCallback(async () => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (sessionId) await api.stopChat(sessionId);
    setStreaming(false);
  }, [sessionId]);

  return { messages, streaming, streamingContent, streamingSources, error, send, stop, loadHistory };
}
