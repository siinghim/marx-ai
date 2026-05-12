"use client";
import { useState, useEffect, useCallback } from "react";
import { Session } from "@/lib/types";
import * as api from "@/lib/api";

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listSessions();
      setSessions(list);
    } catch { /* server not ready */ }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const create = useCallback(async (title?: string) => {
    try {
      const s = await api.createSession(title);
      setSessions((prev) => [s, ...prev]);
      setActiveId(s.id);
      return s;
    } catch { return null; }
  }, []);

  const remove = useCallback(async (id: string) => {
    await api.deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeId === id) setActiveId(null);
  }, [activeId]);

  const select = useCallback((id: string) => { setActiveId(id); }, []);

  return { sessions, activeId, loading, refresh, create, remove, select };
}
