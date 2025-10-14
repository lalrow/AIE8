# --- Logging Utility ---
import json, os, time, re

def log_run(config, runtime, status="success", report_text=None):
    """Logs each Deep Research run with key metrics and saves to JSON."""
    
    section_count = len(re.findall(r"^## ", report_text or "", flags=re.MULTILINE))
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "runtime_sec": round(runtime, 1),
        "config": config.get("configurable", {}),
        "model": config.get("configurable", {}).get("research_model"),
        "sections": section_count,
        "report_length": len(report_text or ""),
        "depth_score": "Excellent" if section_count >= 8 else "Moderate",
        "full_report": report_text,
    }

    os.makedirs("logs", exist_ok=True)
    with open("logs/deep_research_runs.json", "a", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False)
        f.write("\n")

    print(f"✅ Logged run ({status}) → {section_count} sections, {round(runtime,1)} s")
