# `backend/pipeline.py` - The Central Orchestrator

Think of the `PipelineOrchestrator` as the General Manager of a factory. It doesn't actually perform the mathematical algorithms itself, but it imports all the disparate classes (`QualityFilter`, `DeduplicationEngine`, `SmartImputer`) and forces them to execute in a strict, chronological sequence.

## Full Working Process & Logic

### 1. Central State Management
- **Logic**: It initializes a massive dictionary: `self.metadata = {"schema_mapping": {}, "imputation_stats": [], ...}`.
- **Why**: As data moves from one phase to the next, scripts need context. The `SmartImputer` needs to know what the `SchemaAgent` decided in Phase 2. By passing this `self.metadata` dictionary sequentially down the line, every script has access to the full historical context.

### 2. The 12-Phase Execution Hierarchy
The `execute()` method runs a rigid `try-except` wrapped sequence:
1. **Phase 1: Ingestion**: Calls `UniversalLoader` to read the CSV into a Pandas `df`.
2. **Phase 1.5: Profiling**: Calls `DataProfiler` to calculate the starting Quality Score (0-100).
3. **Phase 2: Semantic AI**: Passes the `df` to `SchemaAgent` to classify columns (`email`, `currency`).
4. **Phase 3: Domain AI**: Calls `DomainProfiler` to detect the industry (e.g., `Healthcare`).
5. **Phase 3.5: Quality Filtering**: Calls `QualityFilter.filter_useless_data()` to aggressively nuke >90% empty columns and missing critical rows.
6. **Phase 4 & 5: Format & Translate**: Runs `StringCleaner`, `CurrencyConverter`, and `MultilingualEngine`. (These must run *before* deduplication so that strings are standardized).
7. **Phase 6 & 8: Deduplication**: Runs `DeduplicationEngine` and `EntityResolution` to merge duplicate rows.
8. **Phase 7: Imputation Planning**: Passes the schema to `PlannerAgent` to write JSON "IF-THEN" rules.
9. **Phase 9 & 10: Mathematical Fills**: Runs `SmartImputer` (using the LLM rules and statistical Means) and `OutlierHandler` (IQR clipping).
10. **Phase 11: Validation**: Passes the cleaned `df` to the `Validator` for mathematical hard-checks, and `ValidationAgent` for AI logical auditing.
11. **Phase 12: Export**: Calls `exporter.py` to write the final `.csv` and Markdown reports.

### 3. Graceful Error Handling
Each phase is wrapped in a dedicated `try-except Exception as e:` block. If the Multilingual Translation engine crashes because an API timeout occurred, the Orchestrator logs the error (`log(f"Phase 5 Failed: {e}")`) and simply skips to Phase 6. This guarantees that one minor failure doesn't destroy the user's entire dataset cleaning session.
