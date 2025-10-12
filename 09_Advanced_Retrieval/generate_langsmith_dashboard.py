#!/usr/bin/env python3
"""
Generate HTML Dashboard for LangSmith Evaluation Results
Reads: langsmith_eval_results.json (expected format per notebook export)
Generates: langsmith_dashboard.html
"""

import json
from pathlib import Path


def load_json(path: Path):
    if not path.exists():
        print(f"❌ Error: {path.name} not found! Run the LangSmith export cell to create it.")
        return None
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception as e:
            print(f"❌ Failed to parse {path.name}: {e}")
            return None


def fmt(x, nd=3):
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "N/A"


def main():
    data_path = Path("langsmith_eval_results.json")
    data = load_json(data_path)
    if not data:
        return False

    # Normalize keys and defaults
    rows = []
    for r in data:
        rows.append({
            "Retriever": r.get("Retriever", "Unknown"),
            "QA_Score": r.get("QA_Score"),
            "Helpfulness": r.get("Helpfulness"),
            "Dopeness": r.get("Dopeness"),
            "Latency": r.get("Latency"),
        })

    # Sort by QA_Score desc (fallback to 0)
    rows.sort(key=lambda x: (x["QA_Score"] if isinstance(x["QA_Score"], (int, float)) else -1), reverse=True)

    retrievers = [r["Retriever"] for r in rows]
    qa = [r["QA_Score"] if r["QA_Score"] is not None else 0 for r in rows]
    helpful = [r["Helpfulness"] if r["Helpfulness"] is not None else 0 for r in rows]
    dope = [r["Dopeness"] if r["Dopeness"] is not None else 0 for r in rows]
    latency = [r["Latency"] if r["Latency"] is not None else 0 for r in rows]

    top = rows[0]["Retriever"] if rows else "N/A"

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>LangSmith Evaluation Dashboard - Session 9</title>
  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\" />
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js\"></script>
  <style>
    body {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); min-height: 100vh; padding: 2rem 0; }}
    .container {{ background: #fff; border-radius: 15px; padding: 2rem; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
    h1 {{ color: #11998e; font-weight: bold; margin-bottom: 1.5rem; }}
    .metric-card {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: #fff; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem; text-align: center; }}
    .metric-card h3 {{ font-size: 2.2rem; font-weight: 800; margin: 0; }}
    .metric-card p {{ margin: 0; opacity: .95; }}
    .table-hover tbody tr:hover {{ background-color: #f4fff7; }}
    .best {{ background-color: #d4edda !important; font-weight: 600; }}
    .chart-container {{ position: relative; height: 400px; margin: 2rem 0; }}
    .footer {{ text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #dee2e6; color: #6c757d; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>🧪 LangSmith Evaluation Dashboard</h1>
    <p class=\"lead\">Session 9: Advanced Retrieval - LangSmith QA/Helpfulness/Dopeness</p>

    <div class=\"row mb-4\">
      <div class=\"col-md-4\"><div class=\"metric-card\"><h3>{len(rows)}</h3><p>Retrievers Evaluated</p></div></div>
      <div class=\"col-md-4\"><div class=\"metric-card\"><h3>3</h3><p>LangSmith Metrics</p></div></div>
      <div class=\"col-md-4\"><div class=\"metric-card\"><h3>{top}</h3><p>Top by QA Score</p></div></div>
    </div>

    <h2>📋 LangSmith Results</h2>
    <div class=\"table-responsive\">
      <table class=\"table table-hover table-striped\">
        <thead class=\"table-dark\"><tr>
          <th>Rank</th><th>Retriever</th><th>QA Score</th><th>Helpfulness</th><th>Dopeness</th><th>Latency (s)</th>
        </tr></thead>
        <tbody>
    """

    for i, r in enumerate(rows, 1):
        cls = "best" if i == 1 else ""
        html += (
            f"<tr class=\"{cls}\"><td><strong>{i}</strong></td>"
            f"<td><strong>{r['Retriever']}</strong></td>"
            f"<td>{fmt(r['QA_Score'])}</td><td>{fmt(r['Helpfulness'])}</td>"
            f"<td>{fmt(r['Dopeness'])}</td><td>{fmt(r['Latency'], 2)}</td></tr>"
        )

    html += f"""
        </tbody>
      </table>
    </div>

    <h2 class=\"mt-5\">📈 Score Comparison</h2>
    <div class=\"chart-container\"><canvas id=\"scoreChart\"></canvas></div>

    <div class=\"chart-container\"><canvas id=\"latencyChart\"></canvas></div>

    <div class=\"footer\">
      <p><strong>Generated from:</strong> langsmith_eval_results.json</p>
      <p><strong>Session 9:</strong> Advanced Retrieval</p>
    </div>
  </div>

  <script>
    const labels = {json.dumps(retrievers)};
    const qa = {json.dumps(qa)};
    const helpful = {json.dumps(helpful)};
    const dope = {json.dumps(dope)};
    const latency = {json.dumps(latency)};

    new Chart(document.getElementById('scoreChart').getContext('2d'), {{
      type: 'bar',
      data: {{ labels: labels, datasets: [
        {{ label: 'QA Score', data: qa, backgroundColor: 'rgba(17, 153, 142, 0.85)' }},
        {{ label: 'Helpfulness', data: helpful, backgroundColor: 'rgba(56, 239, 125, 0.85)' }},
        {{ label: 'Dopeness', data: dope, backgroundColor: 'rgba(80, 200, 120, 0.85)' }}
      ]}},
      options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, max: 1.0 }} }} }}
    }});

    new Chart(document.getElementById('latencyChart').getContext('2d'), {{
      type: 'bar',
      data: {{ labels: labels, datasets: [{{ label: 'Latency (s)', data: latency, backgroundColor: 'rgba(255, 159, 64, 0.85)' }}] }},
      options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
  </script>
</body>
</html>
"""

    out = Path("langsmith_dashboard.html")
    out.write_text(html, encoding="utf-8")
    print(f"✅ Generated: {out.resolve()}")
    print("Open with: xdg-open langsmith_dashboard.html (Linux) or start/open on your OS")
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("🧪 LangSmith HTML Dashboard Generator")
    print("=" * 80)
    main()
