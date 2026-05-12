"use client";
import Badge from "./Badge";
import { Session } from "@/lib/types";

interface Props {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

export default function Sidebar({ sessions, activeId, onSelect, onCreate, onDelete }: Props) {
  return (
    <div className="w-64 h-screen bg-gray-900 flex flex-col">
      <Badge />
      <button
        onClick={onCreate}
        className="mx-3 mt-3 px-4 py-2 text-sm bg-red-700 hover:bg-red-600 text-white rounded-lg transition-colors"
      >
        + 新对话
      </button>
      <div className="flex-1 overflow-y-auto mt-2 px-2">
        {sessions.map((s) => (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`group flex items-center justify-between px-3 py-2 my-1 rounded-lg cursor-pointer text-sm transition-colors ${
              s.id === activeId ? "bg-gray-700 text-white" : "text-gray-300 hover:bg-gray-800"
            }`}
          >
            <span className="truncate flex-1">{s.title}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 ml-2 transition-opacity"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
