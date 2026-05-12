"use client";
import Badge from "./Badge";
import { Session } from "@/lib/types";

interface Props {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onOpenSettings: () => void;
}

export default function Sidebar({ sessions, activeId, onSelect, onCreate, onDelete, onOpenSettings }: Props) {
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

      {/* Settings button at bottom */}
      <button
        onClick={onOpenSettings}
        className="mx-3 mb-3 px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors flex items-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        设置
      </button>
    </div>
  );
}
