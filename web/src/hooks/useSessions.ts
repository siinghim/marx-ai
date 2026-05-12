"use client";
import { useState, useEffect, useCallback } from "react";
import { Session } from "@/lib/types";
import * as api from "@/lib/api";

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listSessions();
      setSessions(list);
      setBackendError(null);
    } catch {
      setBackendError("无法连接后端服务，请确认已启动 python server/main.py");
    }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const create = useCallback(async (title?: string) => {
    try {
      const s = await api.createSession(title);
      setSessions((prev) => [s, ...prev]);
      setActiveId(s.id);
      setBackendError(null);
      return s;
    } catch {
      setBackendError("创建对话失败，请确认后端服务已启动");
      return null;
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    await api.deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeId === id) setActiveId(null);
  }, [activeId]);

  const select = useCallback((id: string) => { setActiveId(id); }, []);

  return { sessions, activeId, loading, backendError, refresh, create, remove, select };
}
