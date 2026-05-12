"use client";
import { useState, useEffect } from "react";
import { LLMConfig } from "@/lib/types";
import { loadConfig, saveConfig } from "@/lib/llmConfig";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: LLMConfig) => void;
}

export default function SettingsModal({ isOpen, onClose, onSave }: Props) {
  const [config, setConfig] = useState<LLMConfig>(loadConfig());

  useEffect(() => {
    if (isOpen) setConfig(loadConfig());
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    saveConfig(config);
    onSave(config);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-4">API 配置</h2>
        <p className="text-xs text-gray-500 mb-4">
          API Key 仅保存在浏览器本地，随每次请求发送，不会存储在服务器上。
        </p>

        <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
        <input
          type="password"
          value={config.apiKey}
          onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
          placeholder="sk-..."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-red-500"
        />

        <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
        <input
          type="text"
          value={config.baseUrl}
          onChange={(e) => setConfig({ ...config, baseUrl: e.target.value })}
          placeholder="https://api.deepseek.com"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-red-500"
        />

        <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
        <input
          type="text"
          value={config.model}
          onChange={(e) => setConfig({ ...config, model: e.target.value })}
          placeholder="deepseek-chat"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-6 focus:outline-none focus:ring-2 focus:ring-red-500"
        />

        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm bg-red-700 text-white rounded-lg hover:bg-red-600 transition-colors"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
}
