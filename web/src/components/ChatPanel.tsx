"use client";
import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import MessageBubble from "./MessageBubble";
import MessageInput from "./MessageInput";

interface Props { sessionId: string | null; }

export default function ChatPanel({ sessionId }: Props) {
  const { messages, streaming, streamingContent, streamingSources, error, send, stop, loadHistory } = useChat(sessionId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { loadHistory(); }, [sessionId, loadHistory]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingContent]);

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {!sessionId && (
            <div className="text-center text-gray-400 mt-20">
              <div className="text-6xl mb-4">★</div>
              <p className="text-lg">Marx AI — 马克思主义政治经济学知识库</p>
              <p className="text-sm mt-2">点击左侧"新对话"开始提问</p>
            </div>
          )}
          {sessionId && messages.length === 0 && !streaming && (
            <div className="text-center text-gray-400 mt-20">
              <p className="text-lg">开始提问吧</p>
            </div>
          )}
          {messages.map((msg) => (<MessageBubble key={msg.id} message={msg} />))}
          {streaming && (
            <MessageBubble
              message={{ id: 0, session_id: sessionId || "", role: "assistant", content: "", sources: [], created_at: "" }}
              streamingContent={streamingContent} streamingSources={streamingSources} isStreaming
            />
          )}
          {error && <div className="text-center text-red-500 text-sm my-2">错误: {error}</div>}
          <div ref={bottomRef} />
        </div>
      </div>
      <MessageInput onSend={send} onStop={stop} streaming={streaming} disabled={!sessionId} />
    </div>
  );
}
