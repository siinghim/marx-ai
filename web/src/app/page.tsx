"use client";
import { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";
import SettingsModal from "@/components/SettingsModal";
import { useSessions } from "@/hooks/useSessions";
import { LLMConfig } from "@/lib/types";
import { loadConfig } from "@/lib/llmConfig";

export default function Home() {
  const { sessions, activeId, backendError, create, remove, select } = useSessions();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);

  useEffect(() => {
    setLlmConfig(loadConfig());
  }, []);

  useEffect(() => {
    if (!activeId && sessions.length === 0) { create(); }
  }, [activeId, sessions.length, create]);

  const handleSaveConfig = useCallback((config: LLMConfig) => {
    setLlmConfig(config);
  }, []);

  return (
    <div className="flex h-screen">
      {backendError && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white text-center py-2 text-sm">
          {backendError}
        </div>
      )}
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={select}
        onCreate={() => create()}
        onDelete={remove}
        onOpenSettings={() => setSettingsOpen(true)}
      />
      <div className="flex-1"><ChatPanel sessionId={activeId} llmConfig={llmConfig} /></div>
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSave={handleSaveConfig}
      />
    </div>
  );
}
