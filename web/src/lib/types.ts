export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  created_at: string;
}

export interface Source {
  index: number;
  title: string;
  url: string;
  chunk_id: string;
  author_hint: string;
  date_hint: string;
  score: number;
}

export interface LLMConfig {
  apiKey: string;
  baseUrl: string;
  model: string;
  temperature: number;
  maxTokens: number;
  topP: number;
  topk: number;
  maxCandidates: number;
}
