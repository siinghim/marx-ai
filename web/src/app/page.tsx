"use client";
import { useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";
import { useSessions } from "@/hooks/useSessions";

export default function Home() {
  const { sessions, activeId, backendError, create, remove, select } = useSessions();

  useEffect(() => {
    if (!activeId && sessions.length === 0) { create(); }
  }, [activeId, sessions.length, create]);

  return (
    <div className="flex h-screen">
      {backendError && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white text-center py-2 text-sm">
          {backendError}
        </div>
      )}
      <Sidebar sessions={sessions} activeId={activeId} onSelect={select} onCreate={() => create()} onDelete={remove} />
      <div className="flex-1"><ChatPanel sessionId={activeId} /></div>
    </div>
  );
}
