# Component classification

The classification below is architectural, not a claim that every component
is equally useful. Experimental results determine whether a component should
be retained.

| Component | Class | Why |
|---|---|---|
| `planning_agent.py` | Agent | Uses an LLM to choose extraction handling based on the input. |
| `extraction_agent.py` | Agent | LLM performs extraction and can select tools during extraction. |
| `reflection_agent.py` | Agent | LLM re-checks and can revise extracted data. |
| `verification_agent.py` | Agent | LLM selectively re-extracts low-confidence fields. |
| `recommendation_agent.py` | Agent | LLM produces resume/JD fit reasoning. |
| `validation_agent.py` | Deterministic Service | Pydantic/schema and confidence validation; no model decision. |
| `scoring_agent.py` | Deterministic Service | Date arithmetic, keyword overlap, and scoring are deterministic. |
| `memory.py` | Deterministic Service | Version persistence/diffing. |
| `semantic_memory.py` | Tool/Service boundary | Uses an embedding API plus local persistence for retrieval; evaluated separately as memory infrastructure. |
| `email_validator.py` | Tool | Callable utility used by extraction. |
| `date_parser.py` | Tool | Callable date-normalization utility. |
| `skill_normalizer.py` | Tool | Callable skill-normalization utility. |
| `pdf_parser.py` | Tool | Converts PDF input to text. |
| `agent_graph.py` | Infrastructure | Executes state transitions and records traces. |
| `llm_client.py` | Infrastructure | Shared API client and evaluation telemetry wrapper. |
| `utils/logging_config.py` | Infrastructure | Logging/observability. |
| `utils/retry.py` | Infrastructure | Retry mechanics; not an autonomous decision-maker. |
| `security.py` | Infrastructure | Input/security controls. |
| `schema.py` | Infrastructure | Shared data contract. |

## Memory limitation

The current semantic-memory implementation retrieves similar past resumes
**after extraction and scoring**. Therefore retrieval cannot causally change
the extraction decision in this experiment. The evaluation measures its cost
and any downstream observable effect, but it does not claim a memory-driven
accuracy improvement without evidence. This is intentional rather than a
fabricated positive result.
