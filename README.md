# Spectre — 马克思主义政治经济学智能问答系统

基于 RAG（检索增强生成）的马克思主义文献知识库与对话应用。本地 FAISS 向量索引 + 大语言模型（DeepSeek/OpenAI 兼容），让经典理论可检索、可对话、可分析。

## 架构

```
前端 (Next.js 14)  ──SSE──▶  FastAPI 后端  ──stream──▶  LLM API
                                  │
                                  ├── mia/retriever  ── FAISS 向量检索
                                  ├── mia/rag         ── 上下文构建 + 提示词
                                  └── mia/indexer     ── 增量索引 / 全量重建
```

## 数据流水线

```
爬取 (marxists.org) → 清洗 (HTML/PDF 提取) → 分块 → 向量嵌入 → FAISS 索引
                                     ↓
                              增量模式 / 断点续传
```

## 快速开始

### 环境

- Python 3.10+ (推荐 3.12)
- Node.js 24+
- CUDA (可选，加速 embedding)

### 启动

```bash
# 设置 API Key (或在前端设置面板中配置)
export DEEPSEEK_API_KEY=your_key

# 一键启动
./start.sh

# 或指定端口
./start.sh 8888
```

访问 `http://localhost:3000` 即可使用。

### 数据构建

```bash
# 1. 爬取 marxists.org 中文站
python scripts/crawl.py --out data/mia_raw --resume --max-pages 2000

# 2. 增量清洗
python scripts/clean.py --root data/mia_raw --out data/mia_clean --incremental

# 3. 构建/重建索引
python scripts/index.py --docs data/mia_clean/docs_clean.jsonl --out data/mia_index --rebuild
```

## 项目结构

```
spectre/
├── mia/              # 共享库 (11 模块)
│   ├── schemas.py    # 数据模型
│   ├── config.py     # YAML 配置 + 环境变量
│   ├── crawler.py    # 爬虫 (resume/断点续传)
│   ├── cleaner.py    # 文本清洗 (增量模式)
│   ├── chunker.py    # 文本分块
│   ├── embedder.py   # BAAI/bge-m3 嵌入封装
│   ├── indexer.py    # FAISS 索引 (增量/重建)
│   ├── retriever.py  # 向量检索 + 过滤去重
│   ├── rag.py        # RAG 编排
│   └── llm_client.py # LLM 异步流式调用
├── scripts/          # CLI 入口
├── server/           # FastAPI 后端 (SSE 流式)
├── web/              # Next.js 前端 (Chat UI)
└── config.yaml       # 统一配置
```

## 致谢

"A spectre is haunting the internet — the spectre of Marx."

—— Karl Marx & Friedrich Engels, *Manifesto of the Communist Party*, 1848
