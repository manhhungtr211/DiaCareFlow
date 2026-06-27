# Contract: CLI Ask Command v2 (Backward Compatible)

## Overview

Lệnh `python -m src.cli ask` giữ nguyên interface cho end user, nhưng bên dưới sử dụng LangGraph Multi-Agent pipeline thay vì sequential pipeline.

## Interface

```bash
# Không thay đổi so với Tuần 1
python -m src.cli ask [--top-k N]
```

### Input

- Interactive prompt: nhận câu hỏi từ stdin
- `--top-k N`: Số chunks retrieve (default: 3)
- Quit: `quit`, `exit`, `q`

### Output

Giữ nguyên format output:

```
📋 Câu trả lời:
{answer_text}

📎 Nguồn:
- {source_1} (score: 0.xxx)
- {source_2} (score: 0.xxx)
```

Khi bị từ chối:
```
📋 Câu trả lời:
⚠️ {refusal_message}
```

### Return Type

```python
# Không thay đổi — vẫn là Answer dataclass
@dataclass
class Answer:
    text: str
    sources: list[ChunkResult] = field(default_factory=list)
    is_refused: bool = False
    refuse_reason: str | None = None
```

### Exit Codes

- `0`: Thành công (thoát bình thường)

## Internal Pipeline Interface

```python
# src/agents/pipeline.py
def ask_langgraph(question: str, top_k: int = 3) -> Answer:
    """
    Entry point cho LangGraph Multi-Agent pipeline.
    Trả về Answer (cùng type với pipeline cũ).
    """
    ...

# src/rag/qa/pipeline.py (modified)
def ask(question_text: str, top_k: int = 3) -> Answer:
    """
    Delegate sang LangGraph pipeline.
    Backward compatible — CLI và evaluation runner không cần thay đổi.
    """
    from src.agents.pipeline import ask_langgraph
    return ask_langgraph(question_text, top_k=top_k)
```

## Backward Compatibility Guarantees

1. **CLI interface**: Không thay đổi arguments, output format, exit codes
2. **Python API**: `src.rag.qa.pipeline.ask(question, top_k)` vẫn hoạt động
3. **Evaluation**: `src/evaluation/runner.py` chạy không cần sửa
4. **Error handling**: Lỗi vẫn trả `Answer` với `is_refused=False` và thông báo lỗi, không crash
