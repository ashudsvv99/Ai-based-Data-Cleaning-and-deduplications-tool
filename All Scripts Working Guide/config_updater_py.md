# `backend/config_updater.py` - The Dynamic Configuration Writer

Configuring hyperparameters dynamically from a graphical web interface requires updating backend Python settings files in-place without corrupting existing values or comments. The `config_updater.py` script solves this through regex-driven file modifications.

## Full Working Process & Logic

### 1. Regex In-place Variable Assignment Replacement
- **Logic**: Reads the contents of `config.py` into a string.
- **Action**: Compiles a multiline regex pattern `^({key}\s*=\s*)([^#\n\r]*)(.*)$` for each key to find variable definitions. It splits the line into three capture groups: the variable name assignment, the current value, and any optional comments.
- **Formatting**: Dictates formatting based on Python datatypes (for example, strings are wrapped in double quotes, and the `LLM_BASE_URL` is formatted with environment-variable fallback protection).
- **Substitution**: Executes `pattern.sub` to overwrite the value while preserving code formatting and inline comments.
- **Write-back**: Flushes the updated string back into `config.py`.
