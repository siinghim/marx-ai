"use client";
import { useState, useRef, useEffect } from "react";

interface Props {
  onSend: (message: string) => void;
  onStop: () => void;
  streaming: boolean;
  disabled: boolean;
}

export default function MessageInput({ onSend, onStop, streaming, disabled }: Props) {
  const [input, setInput] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { if (!streaming) ref.current?.focus(); }, [streaming]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || streaming) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <div className="border-t border-gray-200 p-4 bg-white">
      <div className="flex gap-2 items-end max-w-3xl mx-auto">
        <textarea
          ref={ref}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
          }}
          placeholder={disabled ? "请先创建或选择对话" : "输入问题..."}
          disabled={disabled || streaming}
          rows={2}
          className="flex-1 resize-none border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:bg-gray-100 text-sm"
        />
        {streaming ? (
          <button onClick={onStop} className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors text-sm">
            停止
          </button>
        ) : (
          <button onClick={handleSend} disabled={disabled || !input.trim()}
            className="px-4 py-2 bg-red-700 text-white rounded-lg hover:bg-red-600 disabled:bg-gray-400 transition-colors text-sm">
            发送
          </button>
        )}
      </div>
    </div>
  );
}
