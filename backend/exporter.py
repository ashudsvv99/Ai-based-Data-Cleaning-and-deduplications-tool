"""
Exporter: saves cleaned data and generates cleaning reports.
"""
import os
import json
import pandas as pd
from datetime import datetime
import config


class Exporter:
    """Export cleaned datasets and generate detailed cleaning reports."""

    def export_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """Export the cleaned DataFrame to CSV."""
        os.makedirs(config.EXPORTS_DIR, exist_ok=True)
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cleaned_{timestamp}.csv"
        filepath = os.path.join(config.EXPORTS_DIR, filename)
        df.to_csv(filepath, index=False, encoding="utf-8")
        print(f"  [Export] Saved cleaned data to {filepath}")
        return filepath

    def export_excel(self, df: pd.DataFrame, filename: str = None) -> str:
        """Export the cleaned DataFrame to Excel."""
        os.makedirs(config.EXPORTS_DIR, exist_ok=True)
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cleaned_{timestamp}.xlsx"
        filepath = os.path.join(config.EXPORTS_DIR, filename)
        df.to_excel(filepath, index=False, engine="openpyxl")
        print(f"  [Export] Saved cleaned data to {filepath}")
        return filepath

    def generate_report(self, metadata: dict, filename: str = None) -> str:
        """Generate a Markdown cleaning report."""
        os.makedirs(config.REPORTS_DIR, exist_ok=True)
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cleaning_report_{timestamp}.md"
        filepath = os.path.join(config.REPORTS_DIR, filename)

        lines = [
            "# Data Cleaning Report",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Initial Rows:** {metadata.get('initial_rows', 'N/A')}",
            f"- **Final Rows:** {metadata.get('final_rows', 'N/A')}",
            f"- **Execution Time:** {metadata.get('execution_time_sec', 0):.2f} seconds",
            f"- **Validation Score:** {metadata.get('validation', {}).get('overall_confidence', 'N/A')}%",
            "",
            "## Schema Classification",
        ]

        schema = metadata.get("schema_mapping", {})
        if schema:
            lines.append("| Column | Type | Imputation | Multilingual |")
            lines.append("|--------|------|------------|-------------|")
            for col, info in schema.items():
                sem = info.get("semantic_type", "?")
                imp = info.get("imputation_strategy", "?")
                ml = "Yes" if info.get("needs_multilingual", False) else "No"
                lines.append(f"| {col} | {sem} | {imp} | {ml} |")

        lines.append("")
        lines.append("## Translation/Transliteration Stats")
        stats = metadata.get("translation_stats", {})
        if stats:
            for col, data in stats.items():
                lines.append(f"### {col}")
                lines.append(f"- Task: {data.get('task', '?')}")
                lines.append(f"- Items Processed: {data.get('items_processed', data.get('llm_translated', '?'))}")
        else:
            lines.append("No multilingual processing was required.")

        lines.append("")
        lines.append("## Smart Imputation Rules Applied")
        rules = metadata.get("smart_imputation_rules", [])
        if rules:
            for r in rules:
                lines.append(f"- **{r['column']}**: IF {r['condition']} THEN fill '{r['fill_value']}' ({r['rows_filled']} rows, {r['confidence']}% confidence)")
        else:
            lines.append("No smart imputation rules were generated.")

        lines.append("")
        lines.append("## Validation Issues")
        validation = metadata.get("validation", {})
        issues = validation.get("issues", [])
        if issues:
            for issue in issues:
                lines.append(f"- {issue}")
        else:
            lines.append("No validation issues found.")

        report_text = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"  [Export] Saved cleaning report to {filepath}")
        return filepath

    def save_audit_trail(self, metadata: dict, filename: str = None) -> str:
        """Save the full metadata as a JSON audit trail."""
        os.makedirs(config.REPORTS_DIR, exist_ok=True)
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_trail_{timestamp}.json"
        filepath = os.path.join(config.REPORTS_DIR, filename)

        # Make metadata JSON-serializable
        def make_serializable(obj):
            if isinstance(obj, pd.Timestamp):
                return str(obj)
            if hasattr(obj, "dict"):
                return obj.dict()
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=make_serializable, ensure_ascii=False)
        print(f"  [Export] Saved audit trail to {filepath}")
        return filepath
