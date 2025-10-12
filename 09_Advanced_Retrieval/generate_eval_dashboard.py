#!/usr/bin/env python3
"""
Generate HTML Dashboard for Retriever Evaluation Results
Reads: ragas_eval_results.json (required)
Generates: eval_dashboard.html
"""

import json
import os
from pathlib import Path

def generate_html_dashboard():
    """Generate interactive HTML dashboard from evaluation results"""
    
    # Check if RAGAS results exist
    ragas_file = Path('ragas_eval_results.json')
    if not ragas_file.exists():
        print("❌ Error: ragas_eval_results.json not found!")
        print("Please run the notebook evaluation cells first.")
        return False
    
    # Load RAGAS results
    with open(ragas_file, 'r') as f:
        ragas_data = json.load(f)
    
    print(f"✅ Loaded RAGAS data: {len(ragas_data)} retrievers")
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Retriever Evaluation Dashboard - Session 9</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem 0;
        }}
        .container {{
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #667eea;
            font-weight: bold;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }}
        .metric-card h3 {{
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0;
        }}
        .metric-card p {{
            margin: 0;
            opacity: 0.9;
        }}
        table {{
            margin-top: 1rem;
        }}
        .table-hover tbody tr:hover {{
            background-color: #f8f9ff;
        }}
        .best-score {{
            background-color: #d4edda !important;
            font-weight: bold;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 2rem 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Retriever Evaluation Dashboard</h1>
        <p class="lead">Session 9: Advanced Retrieval with LangChain - RAGAS Metrics</p>
        
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="metric-card">
                    <h3>{len(ragas_data)}</h3>
                    <p>Retrievers Evaluated</p>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <h3>3</h3>
                    <p>RAGAS Metrics</p>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <h3>{ragas_data[0].get('Retriever', 'N/A')}</h3>
                    <p>Top Performer</p>
                </div>
            </div>
        </div>
        
        <h2>📋 RAGAS Evaluation Results</h2>
        <div class="table-responsive">
            <table class="table table-hover table-striped">
                <thead class="table-dark">
                    <tr>
                        <th>Rank</th>
                        <th>Retriever</th>
                        <th>Context Precision</th>
                        <th>Context Recall</th>
                        <th>Faithfulness</th>
                        <th>Latency (s)</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add table rows
    for idx, result in enumerate(ragas_data, 1):
        row_class = "best-score" if idx == 1 else ""
        faithfulness = result.get('Faithfulness')
        faithfulness_str = f"{faithfulness:.3f}" if faithfulness is not None else "N/A"
        
        html_content += f"""
                    <tr class="{row_class}">
                        <td><strong>{idx}</strong></td>
                        <td><strong>{result['Retriever']}</strong></td>
                        <td>{result.get('ContextPrecision', 0):.3f}</td>
                        <td>{result.get('ContextRecall', 0):.3f}</td>
                        <td>{faithfulness_str}</td>
                        <td>{result.get('Latency(s)', 0):.2f}</td>
                    </tr>
"""
    
    # Extract data for charts
    retrievers = [r['Retriever'] for r in ragas_data]
    precision = [r.get('ContextPrecision', 0) for r in ragas_data]
    recall = [r.get('ContextRecall', 0) for r in ragas_data]
    faithfulness = [r.get('Faithfulness', 0) if r.get('Faithfulness') is not None else 0 for r in ragas_data]
    latency = [r.get('Latency(s)', 0) for r in ragas_data]
    
    html_content += f"""
                </tbody>
            </table>
        </div>
        
        <h2 class="mt-5">📈 Performance Comparison</h2>
        
        <div class="chart-container">
            <canvas id="metricsChart"></canvas>
        </div>
        
        <div class="chart-container">
            <canvas id="latencyChart"></canvas>
        </div>
        
        <div class="footer">
            <p><strong>Generated from:</strong> ragas_eval_results.json</p>
            <p><strong>Session 9:</strong> Advanced Retrieval with LangChain</p>
            <p><strong>Dataset:</strong> Kids Science PDF (Grade 3)</p>
        </div>
    </div>
    
    <script>
        // Metrics Comparison Chart
        const ctx1 = document.getElementById('metricsChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(retrievers)},
                datasets: [
                    {{
                        label: 'Context Precision',
                        data: {json.dumps(precision)},
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    }},
                    {{
                        label: 'Context Recall',
                        data: {json.dumps(recall)},
                        backgroundColor: 'rgba(118, 75, 162, 0.8)',
                    }},
                    {{
                        label: 'Faithfulness',
                        data: {json.dumps(faithfulness)},
                        backgroundColor: 'rgba(237, 100, 166, 0.8)',
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'RAGAS Metrics by Retriever',
                        font: {{ size: 18 }}
                    }},
                    legend: {{
                        position: 'top',
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 1.0,
                        title: {{
                            display: true,
                            text: 'Score'
                        }}
                    }}
                }}
            }}
        }});
        
        // Latency Chart
        const ctx2 = document.getElementById('latencyChart').getContext('2d');
        new Chart(ctx2, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(retrievers)},
                datasets: [{{
                    label: 'Latency (seconds)',
                    data: {json.dumps(latency)},
                    backgroundColor: 'rgba(255, 159, 64, 0.8)',
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Evaluation Latency by Retriever',
                        font: {{ size: 18 }}
                    }},
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Time (seconds)'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    # Write HTML file
    output_file = Path('eval_dashboard.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Generated: {output_file.absolute()}")
    print(f"\n🌐 To view: Open {output_file} in your browser")
    print(f"   or run: open {output_file}  (macOS)")
    print(f"   or run: xdg-open {output_file}  (Linux)")
    
    return True

if __name__ == "__main__":
    print("="*80)
    print("🎨 HTML Dashboard Generator")
    print("="*80)
    generate_html_dashboard()

