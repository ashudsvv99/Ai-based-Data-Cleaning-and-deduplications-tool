# `backend/state_manager.py` - The Persistent State & Cache Manager

Streamlit applications run in a stateless sandbox that re-executes the main script from top to bottom on every user interaction. `state_manager.py` handles serialization of connection states and cleaned data frames to prevent losing state on hard page refreshes.

## Full Working Process & Logic

### 1. Hidden Local Directory Cache
- **Logic**: Creates a hidden `.cache/` folder in the project root directory.
- **Action**: Provides class methods to serialize the processed DataFrame, session logs, and run metadata using `pickle` in binary mode to `pipeline_state.pkl`.
- **Database Credential Cache**: Saves database hostnames, usernames, port configurations, and schemas into a local `db_credentials.json` file.
- **State Restore & Clear**: Exposes methods to retrieve cached states on page load (`load_pipeline_state`) or delete the serialized cache entirely (`clear_pipeline_state`) when a new cleaning run is initiated.
