"use client";
import { useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";
import { useSessions } from "@/hooks/useSessions";

export default function Home() {
  const { sessions, activeId, create, remove, select } = useSessions();

  useEffect(() => {
    if (!activeId && sessions.length === 0) { create(); }
  }, [activeId, sessions.length, create]);

  return (
    <div className="flex h-screen">
      <Sidebar sessions={sessions} activeId={activeId} onSelect={select} onCreate={() => create()} onDelete={remove} />
      <div className="flex-1"><ChatPanel sessionId={activeId} /></div>
    </div>
  );
}
