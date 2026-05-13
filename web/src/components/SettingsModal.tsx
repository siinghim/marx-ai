"use client";
import { useState, useEffect } from "react";
import { LLMConfig } from "@/lib/types";
import { loadConfig, saveConfig } from "@/lib/llmConfig";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: LLMConfig) => void;
}

const DEFAULTS: LLMConfig = {
  apiKey: "",
  baseUrl: "https://api.deepseek.com",
  model: "deepseek-chat",
  temperature: 0.2,
  maxTokens: 1200,
  topP: 0.9,
};

export default function SettingsModal({ isOpen, onClose, onSave }: Props) {
  const [config, setConfig] = useState<LLMConfig>(DEFAULTS);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setConfig(loadConfig());
  }, []);

  useEffect(() => {
    if (isOpen && mounted) setConfig(loadConfig());
  }, [isOpen, mounted]);

  if (!isOpen || !mounted) return null;

  const handleSave = () => {
    saveConfig(config);
    onSave(config);
    onClose();
  };

  const inputClass = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-4">API 配置</h2>
        <p className="text-xs text-gray-500 mb-4">
          API Key 仅保存在浏览器本地，随每次请求发送，不会存储在服务器上。
        </p>

        <label className={labelClass}>API Key</label>
        <input
          type="password"
          value={config.apiKey}
          onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
          placeholder="sk-..."
          className={inputClass + " mb-4"}
        />

        <label className={labelClass}>Base URL</label>
        <input
          type="text"
          value={config.baseUrl}
          onChange={(e) => setConfig({ ...config, baseUrl: e.target.value })}
          placeholder="https://api.deepseek.com"
          className={inputClass + " mb-4"}
        />

        <label className={labelClass}>Model</label>
        <input
          type="text"
          value={config.model}
          onChange={(e) => setConfig({ ...config, model: e.target.value })}
          placeholder="deepseek-chat"
          className={inputClass + " mb-4"}
        />

        <div className="grid grid-cols-3 gap-3 mb-4">
          <div>
            <label className={labelClass}>Temperature</label>
            <input
              type="number"
              min={0} max={2} step={0.1}
              value={config.temperature}
              onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) || 0 })}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Max Tokens</label>
            <input
              type="number"
              min={1} max={32000} step={1}
              value={config.maxTokens}
              onChange={(e) => setConfig({ ...config, maxTokens: parseInt(e.target.value) || 1 })}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Top P</label>
            <input
              type="number"
              min={0} max={1} step={0.05}
              value={config.topP}
              onChange={(e) => setConfig({ ...config, topP: parseFloat(e.target.value) || 0 })}
              className={inputClass}
            />
          </div>
        </div>

        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors">
            取消
          </button>
          <button onClick={handleSave} className="px-4 py-2 text-sm bg-red-700 text-white rounded-lg hover:bg-red-600 transition-colors">
            保存
          </button>
        </div>
      </div>
    </div>
  );
}
