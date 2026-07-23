# Data Model: UC-012 — Multi-Agent Refactor

**Date**: 2026-07-17 | **Feature**: UC-012

---

## AgentState (Updated)

File: `src/agents/state.py`

```python
class AgentState(MessagesState):
    # === UNCHANGED FIELDS ===
    user_input: str                        # Original user question
    is_safe: bool                          # Triage Agent safety flag
    harm_task: SafetyCategory              # Safety classification
    intent: str                            # SMALL_TALK | DIABETES (giữ tạm, xem OPEN QUESTION)
    small_talk_reply: str                  # Pre-generated reply for SMALL_TALK
    suggestion_context: dict               # Final answer + metadata (Response Agent output)
    messageId: str                         # Message tracking ID
    nodes_visited: Annotated[list[str], operator.add]  # Visited nodes log
    chat_history: list                     # Trimmed history for LLM

    # === REMOVED FIELDS ===
    # rag_context: list   <- Loại bỏ, không còn dùng single RAG node

    # === NEW FIELDS (UC-012) ===
    factor_results:     Annotated[list[dict], operator.add]
    # Ghi bởi: factor_agent_node
    # Format: [{"factor_summary": str, "sources": list[dict]}]

    suggestion_results: Annotated[list[dict], operator.add]
    # Ghi bởi: suggestion_agent_node
    # Format: [{"suggestion_summary": str, "sources": list[dict]}]

    harm_results:   Annotated[list[dict], operator.add]
    # Ghi bởi: harm_agent_node
    # Format: [{"harm_summary": str}]
  
    errors:             Annotated[list[str], operator.add]      # lỗi trong quá trình xử lý
    follow_up_question: Optional[str] #Nếu câu hỏi chưa đủ rõ ràng thì supervisor sẽ đặt câu hỏi để làm rõ
    factor_question: Optional[str] #Câu hỏi dành cho factor agent
    suggestion_question: Optional[str] #Câu hỏi dành cho suggestion agent
    harm_question: Optional[str] #Câu hỏi dành cho harm agent
    should_response: Optional[bool] #Nếu True thì supervisor sẽ gọi response_agent

```
```python
class FactorState(TypedDict): # state cho rag
    rag_sources: dict #src của nguồn truy xuất từ rag (nếu có): gồm tên file, title, description, chunks, filtered_contexts
    web_sources: dict #src của nguồn truy xuất từ web (nếu có): gồm url, title, snippet, filtered_contexts
    factor_task: str #task từ supervior giao cho
    queries: List[str] #query sinh ra sau khi đưa harm_task vào LLM 
    factor_context: dict # gồm nội dung các response sau khi đưa các query vào LLM và xử lý bởi rag_agent và web_agent, chứa rag_src và web_src
    messageId: str
```
```python
class FactorOutputState(TypedDict): #state này để trả về cho Supervior Node
    factor_results: List[dict] # giống harm_context 
```
```python
class HarmState(TypedDict): # state cho rag
    rag_sources: dict #src của nguồn truy xuất từ rag (nếu có): gồm tên file, title, description, chunks, filtered_contexts
    web_sources: dict #src của nguồn truy xuất từ web (nếu có): gồm url, title, snippet, filtered_contexts
    harm_task: str #task từ supervior giao cho
    queries: List[str] #query sinh ra sau khi đưa harm_task vào LLM 
    harm_context: dict # gồm nội dung các response sau khi đưa các query vào LLM và xử lý bởi rag_agent và web_agent, chứa rag_src và web_src
    messageId: str
```
```python
class HarmOutputState(TypedDict): #state này để trả về cho Supervior Node
    harm_results: List[dict] # giống harm_context 
```
```python
class SuggestionState(TypedDict): # state cho rag
    rag_sources: dict #src của nguồn truy xuất từ rag (nếu có): gồm tên file, title, description, chunks, filtered_contexts
    web_sources: dict #src của nguồn truy xuất từ web (nếu có): gồm url, title, snippet, filtered_contexts
    suggestion_task: str #task từ supervior giao cho
    queries: List[str] #query sinh ra sau khi đưa harm_task vào LLM 
    suggestion_context: dict # gồm nội dung các response sau khi đưa các query vào LLM và xử lý bởi rag_agent và web_agent, chứa rag_src và web_src
    messageId: str
```
```python
class SuggestionOutputState(TypedDict): #state này để trả về cho Supervior Node
    suggestion_results: List[dict] # giống harm_context 
```
---

## Graph Topology (Updated)

File: `src/agents/graph.py`

```
START
  │
  ▼
triage_agent          ← triage_agent_node (rename trong graph, logic giữ nguyên)
  │
  ├─── is_safe=False ──────────────────────────────────┐
  │                                                    │
  ▼ is_safe=True                                       │
supervisor_agent       ← đổi role: fan-out dispatcher │
  │                                                    │
  │ (Send API - parallel)                              │
  ├──► factor_agent                                    │
  ├──► suggestion_agent                                │
  └──► harm_sub_agent                                  │
        │                                              │
        ▼ (fan-in: tất cả 3 nodes xong)               │
     aggregate_node    ← node mới, không gọi LLM      │
        │                                              │
        ▼                                              │
  response_agent ◄────────────────────────────────────┘
        │
        ▼
       END
```

---

## Node Contracts

### triage_agent (= triage_agent_node hiện tại)

| I/O | Field | Type |
|-----|-------|------|
| Reads | `user_input` | str |
| Writes | `is_safe` | bool |
| Writes | `harm_task` | SafetyCategory |
| Writes | `suggestion_context` | dict (refusal_message khi unsafe) |

### supervisor_agent

| I/O | Field | Type |
|-----|-------|------|
| Reads | `user_input`, `is_safe` | str, bool |
| Returns | `Send` objects | list[Send] |
| Note | Không ghi state trực tiếp | — |

### factor_agent (NEW)

| I/O | Field | Type |
|-----|-------|------|
| Reads | `user_input` | str |
| Writes | `factor_results` | list[dict] (appended) |
| Writes | `nodes_visited` | list[str] (appended) |
| Tool | RAG (primary) | retrieve() |

### suggestion_agent (NEW)

| I/O | Field | Type |
|-----|-------|------|
| Reads | `user_input` | str |
| Writes | `suggestion_results` | list[dict] (appended) |
| Writes | `nodes_visited` | list[str] (appended) |
| Tool | WebSearch (primary), RAG (fallback) | web_search(), retrieve() |

### harm_sub_agent (NEW)

| I/O | Field | Type |
|-----|-------|------|
| Reads | `user_input` | str |
| Writes | `harm_sub_results` | list[dict] (appended) |
| Writes | `nodes_visited` | list[str] (appended) |
| Tool | RAG (primary) | retrieve() |

### aggregate_node (NEW — no LLM)

| I/O | Field | Type |
|-----|-------|------|
| Reads | `factor_results`, `suggestion_results`, `harm_sub_results` | list[dict] |
| Writes | Không ghi field mới, chỉ pass-through | — |
| Note | Pure function, hợp nhất kết quả để response_agent đọc | — |

### response_agent (MODIFIED)

| I/O | Field | Type |
|-----|-------|------|
| Reads | `factor_results[0]`, `suggestion_results[0]`, `harm_sub_results[0]` | dict |
| Reads | `user_input`, `chat_history` | str, list |
| Writes | `suggestion_context` | dict |

---

## Enum / Model không thay đổi

- `SafetyCategory`: SAFE, PRESCRIPTION, DIAGNOSIS, EMERGENCY — giữ nguyên
- `Answer` dataclass — giữ nguyên
- `WebSearchResponse` — giữ nguyên
