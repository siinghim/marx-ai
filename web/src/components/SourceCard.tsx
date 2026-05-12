"use client";
import { useState } from "react";
import { Source } from "@/lib/types";

export default function SourceCard({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-2 border border-gray-200 rounded-lg bg-gray-50">
      <button onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-3 py-2 text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
        <span>{expanded ? "▾" : "▸"}</span>
        <span>来源 ({sources.length})</span>
      </button>
      {expanded && (
        <div className="px-3 pb-2 space-y-1">
          {sources.map((s) => (
            <div key={s.chunk_id} className="text-xs text-gray-600">
              <span className="font-medium text-red-700">[{s.index}]</span>{" "}
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                {s.title}
              </a>
              {s.author_hint && <span className="ml-1 text-gray-400">— {s.author_hint}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
