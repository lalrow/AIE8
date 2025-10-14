# Call Stack: Open Deep Research - Supervisor-Researcher Architecture

## Overview
This document visualizes the execution flow and call stack for the LangGraph Open Deep Research system as implemented in `open-deep-research.ipynb`.

## Complete Call Stack

```
START
│
├─► [1] clarify_with_user (Main Graph - Entry Point)
│   │   Location: open_deep_library/deep_researcher.py:60-115
│   │   Purpose: Analyzes user messages and asks clarifying questions if needed
│   │   
│   ├─► get_api_key_for_model()
│   │   └─► Returns API key for configured model
│   │
│   ├─► ChatModel (LLM Call)
│   │   └─► Structured Output: ClarifyWithUser
│   │       ├─► needs_clarification: bool
│   │       └─► clarification_question: str
│   │
│   └─► Decision:
│       ├─► If needs_clarification=True: END (wait for user)
│       └─► If needs_clarification=False: Continue to [2]
│
├─► [2] write_research_brief (Main Graph)
│   │   Location: open_deep_library/deep_researcher.py:118-175
│   │   Purpose: Transforms user messages into structured research brief
│   │
│   ├─► get_api_key_for_model()
│   │   └─► Returns API key for configured model
│   │
│   ├─► get_today_str()
│   │   └─► Returns formatted current date
│   │
│   ├─► ChatModel (LLM Call)
│   │   └─► Structured Output: ResearchQuestion
│   │       ├─► research_topic: str
│   │       └─► research_question: str
│   │
│   └─► Initialize supervisor_messages with:
│       ├─► lead_researcher_prompt (system prompt)
│       └─► research_brief (user message)
│
├─► [3] research_supervisor (Supervisor Subgraph Entry)
│   │   This invokes the entire supervisor_subgraph
│   │
│   └─► supervisor_subgraph.invoke()
│       │
│       ├─► [3.1] supervisor (Supervisor Subgraph Node)
│       │   │   Location: open_deep_library/deep_researcher.py:178-223
│       │   │   Purpose: Lead researcher that plans and delegates research
│       │   │
│       │   ├─► get_api_key_for_model()
│       │   │   └─► Returns API key for configured model
│       │   │
│       │   ├─► get_all_tools()
│       │   │   └─► Returns [ConductResearch, ResearchComplete, think_tool]
│       │   │
│       │   ├─► ChatModel (LLM Call with Tools)
│       │   │   └─► AI Message with tool_calls:
│       │   │       ├─► think_tool (strategic reflection)
│       │   │       ├─► ConductResearch (delegate research)
│       │   │       └─► ResearchComplete (signal completion)
│       │   │
│       │   └─► Increment research_iteration counter
│       │
│       ├─► [3.2] supervisor_tools (Supervisor Subgraph Node)
│       │   │   Location: 
/deep_researcher.py:225-349
│       │   │   Purpose: Executes supervisor's tool calls and spawns researchers
│       │   │
│       │   ├─► Check exit conditions:
│       │   │   ├─► research_iteration >= max_researcher_iterations
│       │   │   ├─► No tool calls made
│       │   │   └─► ResearchComplete called
│       │   │
│       │   ├─► Process think_tool calls:
│       │   │   └─► Record strategic reflections in messages
│       │   │
│       │   ├─► Execute ConductResearch calls (PARALLEL):
│       │   │   │   Limit: max_concurrent_research_units (default: 5)
│       │   │   │
│       │   │   └─► For each ConductResearch call:
│       │   │       │
│       │   │       └─► researcher_subgraph.ainvoke() [SPAWNED SUBGRAPH]
│       │   │           │
│       │   │           ├─► [3.2.1] researcher (Researcher Subgraph Node)
│       │   │           │   │   Location: open_deep_library/deep_researcher.py:365-424
│       │   │           │   │   Purpose: Individual researcher conducting focused research
│       │   │           │   │
│       │   │           │   ├─► get_api_key_for_model()
│       │   │           │   │   └─► Returns API key for configured model
│       │   │           │   │
│       │   │           │   ├─► get_all_tools()
│       │   │           │   │   └─► Returns [tavily_search, think_tool, ResearchComplete, MCP tools]
│       │   │           │   │
│       │   │           │   ├─► research_system_prompt (system prompt)
│       │   │           │   │   └─► Includes research question and context
│       │   │           │   │
│       │   │           │   ├─► ChatModel (LLM Call with Tools)
│       │   │           │   │   └─► AI Message with tool_calls:
│       │   │           │   │       ├─► tavily_search (web search)
│       │   │           │   │       ├─► think_tool (reflection)
│       │   │           │   │       └─► ResearchComplete (done)
│       │   │           │   │
│       │   │           │   └─► Increment tool_call_iteration counter
│       │   │           │
│       │   │           ├─► [3.2.2] researcher_tools (Researcher Subgraph Node)
│       │   │           │   │   Location: open_deep_library/deep_researcher.py:435-509
│       │   │           │   │   Purpose: Executes researcher's tool calls
│       │   │           │   │
│       │   │           │   ├─► Check early exit conditions:
│       │   │           │   │   ├─► No tool calls made
│       │   │           │   │   ├─► anthropic_websearch_called()
│       │   │           │   │   └─► openai_websearch_called()
│       │   │           │   │
│       │   │           │   ├─► Execute all tool calls (PARALLEL):
│       │   │           │   │   │
│       │   │           │   │   ├─► tavily_search()
│       │   │           │   │   │   │   Location: open_deep_library/utils.py:43-136
│       │   │           │   │   │   │
│       │   │           │   │   │   ├─► Tavily API call
│       │   │           │   │   │   │   └─► Returns search results
│       │   │           │   │   │   │
│       │   │           │   │   │   ├─► Check content length
│       │   │           │   │   │   │
│       │   │           │   │   │   └─► If > max_content_length:
│       │   │           │   │   │       ├─► get_api_key_for_model()
│       │   │           │   │   │       └─► ChatModel (Summarization)
│       │   │           │   │   │           └─► Summarized content
│       │   │           │   │   │
│       │   │           │   │   ├─► think_tool()
│       │   │           │   │   │   │   Location: open_deep_library/utils.py:219-244
│       │   │           │   │   │   └─► Records strategic thinking
│       │   │           │   │   │
│       │   │           │   │   └─► MCP tools (if configured)
│       │   │           │   │       └─► External tool execution
│       │   │           │   │
│       │   │           │   ├─► Check late exit conditions:
│       │   │           │   │   ├─► tool_call_iteration >= max_react_tool_calls
│       │   │           │   │   └─► ResearchComplete called
│       │   │           │   │
│       │   │           │   └─► Decision:
│       │   │           │       ├─► If exit: Continue to [3.2.3]
│       │   │           │       └─► If continue: Loop back to [3.2.1]
│       │   │           │
│       │   │           └─► [3.2.3] compress_research (Researcher Subgraph Node)
│       │   │               │   Location: open_deep_library/deep_researcher.py:511-585
│       │   │               │   Purpose: Compresses research findings into summary
│       │   │               │
│       │   │               ├─► get_api_key_for_model()
│       │   │               │   └─► Returns API key for compression model
│       │   │               │
│       │   │               ├─► compress_research_system_prompt (system prompt)
│       │   │               │   └─► Instructions for compression
│       │   │               │
│       │   │               ├─► Retry loop (max 3 attempts):
│       │   │               │   │
│       │   │               │   ├─► ChatModel (LLM Call)
│       │   │               │   │   └─► Compressed research output
│       │   │               │   │
│       │   │               │   ├─► is_token_limit_exceeded()
│       │   │               │   │   └─► Check if token limit error
│       │   │               │   │
│       │   │               │   └─► If token limit:
│       │   │               │       ├─► remove_up_to_last_ai_message()
│       │   │               │       │   └─► Truncate messages
│       │   │               │       └─► Retry compression
│       │   │               │
│       │   │               ├─► get_notes_from_tool_calls()
│       │   │               │   └─► Extract raw notes from messages
│       │   │               │
│       │   │               └─► Return:
│       │   │                   ├─► compressed_research: str
│       │   │                   └─► raw_notes: str
│       │   │
│       │   ├─► Aggregate all researcher results:
│       │   │   └─► Collect compressed_research + raw_notes from all researchers
│       │   │
│       │   └─► Decision:
│       │       ├─► If exit condition met: EXIT supervisor_subgraph
│       │       └─► If continue: Loop back to [3.1]
│       │
│       └─► Return accumulated notes to main graph
│
└─► [4] final_report_generation (Main Graph - Final Node)
    │   Location: open_deep_library/deep_researcher.py:607-697
    │   Purpose: Generates comprehensive final research report
    │
    ├─► get_notes_from_tool_calls()
    │   └─► Extract all notes from research
    │
    ├─► get_api_key_for_model()
    │   └─► Returns API key for final report model
    │
    ├─► final_report_generation_prompt (system prompt)
    │   └─► Instructions for report generation
    │
    ├─► Retry loop (max 3 attempts):
    │   │
    │   ├─► ChatModel (LLM Call)
    │   │   └─► Final report content
    │   │
    │   ├─► is_token_limit_exceeded()
    │   │   └─► Check if token limit error
    │   │
    │   └─► If token limit:
    │       ├─► get_model_token_limit()
    │       │   └─► Get model's max token limit
    │       │
    │       ├─► Calculate truncation (reduce by 10%)
    │       │
    │       └─► Retry with truncated content
    │
    └─► Return final_report: str
        │
        END
```

## Execution Flow Summary

### Level 1: Main Graph (Top Level)
```
clarify_with_user → write_research_brief → research_supervisor → final_report_generation
```

### Level 2: Supervisor Subgraph (Middle Level)
```
supervisor → supervisor_tools → (loop back to supervisor)
                 ↓
        (spawns researcher_subgraphs in parallel)
```

### Level 3: Researcher Subgraph (Bottom Level)
```
researcher → researcher_tools → (loop back to researcher)
                    ↓
           (when done: compress_research)
```

## Key Control Flow Decisions

### 1. Clarification Gate
- **Location**: clarify_with_user node
- **Decision**: `needs_clarification == True` → END, wait for user
- **Default**: Continue to research brief

### 2. Supervisor Loop
- **Location**: supervisor_tools node
- **Exit Conditions**:
  - `research_iteration >= max_researcher_iterations`
  - No tool calls made
  - `ResearchComplete` tool called
- **Default**: Loop back to supervisor

### 3. Researcher Loop
- **Location**: researcher_tools node
- **Exit Conditions**:
  - `tool_call_iteration >= max_react_tool_calls`
  - `ResearchComplete` tool called
  - Native web search used (Anthropic/OpenAI)
- **Default**: Loop back to researcher

### 4. Parallel Execution
- **Location**: supervisor_tools node
- **Parallelism**: Up to `max_concurrent_research_units` researchers
- **Mechanism**: `asyncio.gather()` with semaphore limiting

## Configuration Parameters

### Iteration Limits
- `max_researcher_iterations`: Default 6 (supervisor delegation limit)
- `max_react_tool_calls`: Default 10 (researcher tool call limit)
- `max_concurrent_research_units`: Default 5 (parallel researchers)

### Model Configuration
- `research_model`: Used in supervisor and researcher nodes
- `compression_model`: Used in compress_research node
- `final_report_model`: Used in final_report_generation node
- `summarization_model`: Used in tavily_search for long content

### Search Configuration
- `search_api`: ANTHROPIC, TAVILY, or NONE
- `max_content_length`: Character limit before summarization

## Error Handling

### Token Limit Errors
- **compress_research**: Retry up to 3 times with progressive message truncation
- **final_report_generation**: Retry up to 3 times with 10% content reduction per retry

### Tool Execution Errors
- **researcher_tools**: Safe error handling, continues with available results
- **tavily_search**: Graceful fallback if summarization fails

## State Management

### AgentState (Main Graph)
```python
{
    "messages": List[BaseMessage],           # User conversation
    "research_brief": str,                   # Structured research brief
    "notes": List[str],                      # Accumulated research findings
    "final_report": str                      # Final synthesized report
}
```

### SupervisorState (Supervisor Subgraph)
```python
{
    "supervisor_messages": List[BaseMessage], # Supervisor conversation
    "research_iteration": int,                # Current iteration count
    "notes": List[str]                        # Accumulated findings
}
```

### ResearcherState (Researcher Subgraph)
```python
{
    "researcher_messages": List[BaseMessage], # Researcher conversation
    "tool_call_iteration": int,               # Current tool call count
    "compressed_research": str,               # Synthesized findings
    "raw_notes": str                          # Raw research notes
}
```

## Tool Inventory

### Supervisor Tools
1. `ConductResearch` - Delegate research to sub-agent
2. `ResearchComplete` - Signal research completion
3. `think_tool` - Strategic reflection

### Researcher Tools
1. `tavily_search` - Web search with summarization
2. `think_tool` - Reflection on progress
3. `ResearchComplete` - Signal completion
4. MCP tools (if configured)

## Performance Characteristics

### Parallelism
- **Supervisor**: Sequential (one supervisor)
- **Researchers**: Parallel (up to `max_concurrent_research_units`)
- **Tool Calls**: Parallel within each researcher

### Token Usage
- **Compression**: Prevents token overflow in individual researchers
- **Final Report**: Progressive degradation if token limit exceeded
- **Summarization**: Automatic for web search results > `max_content_length`

### Latency
- **Best Case**: All researchers complete in parallel
- **Worst Case**: Sequential supervisor iterations with max researchers each time
- **Typical**: 2-4 supervisor iterations with 3-5 parallel researchers each

## Example Execution Timeline

```
T=0s    : User submits research request
T=2s    : clarify_with_user → no clarification needed
T=5s    : write_research_brief → brief generated
T=8s    : supervisor → plans 5 research tasks
T=10s   : supervisor_tools → spawns 5 parallel researchers
          ├─ Researcher 1: Topic A (3 searches, 2 reflections)
          ├─ Researcher 2: Topic B (2 searches, 1 reflection)
          ├─ Researcher 3: Topic C (4 searches, 3 reflections)
          ├─ Researcher 4: Topic D (2 searches, 1 reflection)
          └─ Researcher 5: Topic E (3 searches, 2 reflections)
T=45s   : All researchers complete → compression
T=50s   : supervisor → decides to delegate 2 more tasks
T=52s   : supervisor_tools → spawns 2 more researchers
T=75s   : All researchers complete → compression
T=78s   : supervisor → calls ResearchComplete
T=80s   : supervisor_subgraph exits
T=95s   : final_report_generation → comprehensive report
T=100s  : END
```

## Diagram: Graph Structure

```
┌─────────────────────────────────────────────────────────┐
│                     Main Graph                          │
│                                                         │
│  START → clarify → brief → supervisor → report → END   │
│                              │                          │
│                              ▼                          │
│                  ┌───────────────────────┐              │
│                  │  Supervisor Subgraph  │              │
│                  │                       │              │
│                  │  supervisor ⟲         │              │
│                  │      ↕                │              │
│                  │  supervisor_tools     │              │
│                  │      ↓                │              │
│                  │  ┌─────────────────┐ │              │
│                  │  │ Researcher      │ │              │
│                  │  │ Subgraph        │ │              │
│                  │  │                 │ │              │
│                  │  │ researcher ⟲    │ │              │
│                  │  │     ↕           │ │              │
│                  │  │ tools           │ │              │
│                  │  │     ↓           │ │              │
│                  │  │ compress        │ │              │
│                  │  └─────────────────┘ │              │
│                  │  (spawned 5x in      │              │
│                  │   parallel)          │              │
│                  └───────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

## File References

All implementation details can be found in:
- **State Definitions**: `open_deep_library/state.py`
- **Node Functions**: `open_deep_library/deep_researcher.py`
- **Utilities & Tools**: `open_deep_library/utils.py`
- **Configuration**: `open_deep_library/configuration.py`
- **Prompts**: `open_deep_library/prompts.py`

## End of Call Stack



