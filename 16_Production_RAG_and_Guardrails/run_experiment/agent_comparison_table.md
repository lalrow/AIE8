# Agent Performance Comparison

## Complex Multi-Tool Query Test

**Query:** "Can you check if there is a proper arXiv paper on 'Hyper-Parameter Optimization' published between 2010 and 2020, and tell me whether its content or methods have become outdated based on newer research after 2020"

---

| Metric | Simple Agent | Helpfulness Agent | Winner |
|--------|--------------|-------------------|--------|
| **Time** | 10.48s | 13.17s | ✅ Simple (25.7% faster) |
| **Messages** | 8 | 12 | ✅ Simple (33% fewer) |
| **Tool Calls** | 6 | 8 | ✅ Simple (25% fewer) |
| **Tools Used** | `arxiv` (6x) | `arxiv` (8x) | - |
| **Missing Tools** | `tavily` ❌ | `tavily` ❌ | Both failed |
| **Completion** | Partial (no newer research) | Failed (hit message cap) | ✅ Simple |
| **Termination** | Normal | `HELPFULNESS:END` (>10 msgs) | ✅ Simple |

---

### Key Findings

- **Speed difference:** Helpfulness Agent was **25.7% slower**
- **Tool efficiency:** Both agents only used Arxiv, neither searched for newer research with Tavily
- **Completion:** Simple Agent provided partial answer; Helpfulness Agent exceeded message limit and terminated early
- **Query success:** ❌ Neither agent fully completed the task (missing comparison with post-2020 research)

---

### Conclusion

For complex multi-tool queries:
- **Simple Agent:** Faster, fewer resources, partial completion
- **Helpfulness Agent:** Slower, more tool calls, failed to converge due to message limit

**Winner:** Simple Agent (completed more of the task in less time)
