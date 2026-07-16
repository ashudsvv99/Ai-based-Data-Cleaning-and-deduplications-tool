# `nl_query_agent.py` - The Text-to-SQL Cognitive Agent

The `agents/nl_query_agent.py` script is a specialized LLM agent responsible for translating plain English questions from the user into executable SQL queries against their live database.

## Full Working Process & Logic

### 1. Contextual Prompting
- **Action**: When a user asks a question (e.g., "Find duplicate records"), the agent requires context to generate valid SQL. 
- The script fetches the live database schema (Table Names, Column Names, and SQL Types) and injects it into a massive System Prompt. It strictly instructs the LLM to act as a Senior SQL Developer and *only* output valid SQL that matches the specific schema.

### 2. JSON Block Extraction
- **Problem**: Local LLMs (especially instruction-tuned ones) have a bad habit of wrapping their SQL in markdown blocks (e.g., \`\`\`sql SELECT * FROM table \`\`\`) or adding conversational filler like "Here is your query:".
- **Solution**: The agent utilizes regex and string parsing techniques to aggressively strip out the markdown and conversational text, isolating the raw, executable SQL string.

### 3. The Self-Correction Loop (Error Recovery)
- **Problem**: AI hallucination might cause the LLM to generate SQL with a syntax error or reference a column that doesn't exist.
- **Solution**: If the `db_pipeline.py` fails to execute the query, it catches the SQLAlchemy Database Error. The `NLQueryAgent` takes that exact error message, feeds it *back* into the LLM as a new prompt ("Your previous query failed with this error. Fix it."), allowing the AI to debug and self-correct its own SQL autonomously.
