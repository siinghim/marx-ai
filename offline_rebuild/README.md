# Spectre 离线索引重建

在无网络、CUDA 12.1 服务器上重建 FAISS 索引。

## 文件清单

```
offline_rebuild/
├── rebuild.py              # 独立重建脚本（无外部依赖）
├── requirements-cu121.txt  # CUDA 12.1 Python 依赖
└── README.md               # 本文件

需要额外传输：
  data/mia_clean/docs_merged.jsonl  # 12,845 篇清洗后文档 (602 MB)
```

## 步骤

### 1. 在有网络的机器上下载依赖包

```bash
mkdir wheels
pip download -r requirements-cu121.txt -d wheels/
# 关键：torch 必须用 CUDA 12.1 版本
pip download torch --index-url https://download.pytorch.org/whl/cu121 -d wheels/
```

### 2. 传输到离线服务器

```bash
# 代码
scp -r offline_rebuild/ user@server:/path/to/

# 数据文件 (602 MB)
scp data/mia_clean/docs_merged.jsonl user@server:/path/to/data/mia_clean/

# pip 包 (如果有 wheels)
scp -r wheels/ user@server:/path/to/wheels/
```

### 3. 在离线服务器上安装

```bash
cd /path/to/offline_rebuild

# 用本地 wheels 安装
pip install --no-index --find-links wheels/ -r requirements-cu121.txt

# 或者如果有网络镜像/内网 pip 源：
# pip install torch --index-url https://download.pytorch.org/whl/cu121
# pip install -r requirements-cu121.txt
```

### 4. 运行重建

```bash
python rebuild.py \
  --docs /path/to/docs_merged.jsonl \
  --out /path/to/index_output \
  --device cuda
```

参数说明：
- `--docs`：清洗后的 JSONL 文档路径
- `--out`：输出目录（存放 sample.index, chunk_meta.json 等）
- `--device`：cuda 或 cpu
- `--batch-size`：嵌入批次大小（默认 32，内存不足可降为 16）
- `--chunk-size`：分块大小（默认 700 字符）

### 5. 拷回索引

```bash
# 输出目录包含：
#   sample.index      — FAISS 向量索引
#   chunk_meta.json   — chunk 元数据
#   chunks.jsonl      — chunk 文本
#   build_info.json   — 构建参数

scp -r /path/to/index_output/ user@main-server:/path/to/spectre/data/mia_index_5000/
```

### 6. 在主服务器重启 Spectre

```bash
cd spectre
./start.sh 8888
```

## 预估

| 项目 | 数值 |
|------|------|
| 文档数 | 12,845 |
| 预估 Chunks | ~370,000 |
| GPU 重建耗时 | ~3.5-4 小时 |
| 索引大小 | ~2-3 GB |
| GPU 显存需求 | ≥ 8 GB VRAM |
| 系统内存需求 | ≥ 16 GB RAM |

## 故障排除

**OOM (显存不足)**：
```bash
python rebuild.py --docs ... --out ... --device cuda --batch-size 16
# 或降为 8
python rebuild.py --docs ... --out ... --device cuda --batch-size 8
```

**模型无法下载**（BAAI/bge-m3 需第一次下载）：
在有网络的机器上先下载缓存，然后拷贝：
```bash
# 在有网络的机器上
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
# 缓存位置：~/.cache/huggingface/hub/models--BAAI--bge-m3/
# 拷贝这个目录到离线服务器的相同路径
```

**FAISS 写入 OOM**（系统内存不足）：
脚本已将 add_with_ids 分批为每次 50,000 个向量。如果仍然 OOM，手动修改 rebuild.py 中的 `sub_batch` 值。
