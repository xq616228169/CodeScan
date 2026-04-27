"""
Report service for CodeScan.

Generates HTML security audit reports.
"""

from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any

from app.models import Task


# Stage configurations for report generation
STAGE_CONFIGS = {
    "rce": {
        "label": "RCE Audit",
        "description": "Remote Code Execution vulnerability analysis",
        "accent": "red"
    },
    "injection": {
        "label": "Injection Audit", 
        "description": "SQL/NoSQL injection vulnerability analysis",
        "accent": "orange"
    },
    "auth": {
        "label": "Auth & Session Audit",
        "description": "Authentication and session management analysis",
        "accent": "blue"
    },
    "access": {
        "label": "Access Control Audit",
        "description": "Access control mechanism analysis",
        "accent": "purple"
    },
    "xss": {
        "label": "XSS Audit",
        "description": "Cross-Site Scripting vulnerability analysis",
        "accent": "yellow"
    },
    "config": {
        "label": "Config & Component Audit",
        "description": "Configuration and component security analysis",
        "accent": "green"
    },
    "fileop": {
        "label": "File Operation Audit",
        "description": "File operation security analysis",
        "accent": "teal"
    },
    "logic": {
        "label": "Business Logic Audit",
        "description": "Business logic vulnerability analysis",
        "accent": "indigo"
    }
}


async def generate_html(task: Task, generated_at: datetime) -> Tuple[Optional[str], str]:
    """
    Generate HTML report for a task.
    
    Returns tuple of (html_content, filename).
    """
    
    # Find completed audit stages (exclude init)
    completed_stages = [
        s for s in task.stages 
        if s.status == "completed" and s.name != "init"
    ]
    
    if not completed_stages:
        return None, ""
    
    # Build report data
    report_data = {
        "task_id": task.id,
        "short_id": task.id[:8],
        "name": task.name or "Unnamed Project",
        "remark": task.remark or "",
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "",
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M"),
        "stages": []
    }
    
    total_findings = 0
    unique_files = set()
    clean_stages = 0
    
    for stage in completed_stages:
        config = STAGE_CONFIGS.get(stage.name, {
            "label": stage.name,
            "description": "",
            "accent": "gray"
        })
        
        findings = stage.output_json if isinstance(stage.output_json, list) else []
        
        stage_data = {
            "name": config["label"],
            "description": config["description"],
            "accent": config["accent"],
            "findings": [],
            "finding_count": len(findings)
        }
        
        for finding in findings:
            if isinstance(finding, dict):
                file_path = finding.get("file", "")
                if file_path:
                    unique_files.add(file_path)
                
                stage_data["findings"].append({
                    "severity": finding.get("severity", "INFO"),
                    "title": finding.get("title", ""),
                    "file": file_path,
                    "line": finding.get("line", 0),
                    "description": finding.get("description", ""),
                    "evidence": finding.get("evidence", ""),
                    "recommendation": finding.get("recommendation", "")
                })
        
        if len(findings) == 0:
            clean_stages += 1
        
        total_findings += len(findings)
        report_data["stages"].append(stage_data)
    
    report_data["summary"] = {
        "completed_stage_count": len(completed_stages),
        "clean_stage_count": clean_stages,
        "total_findings": total_findings,
        "unique_files": len(unique_files)
    }
    
    # Generate filename
    safe_name = "".join(c if c.isalnum() else "_" for c in (task.name or "report"))[:50]
    filename = f"codescan-{safe_name}-{task.id[:8]}.html"
    
    # Render HTML
    html = render_html_template(report_data)
    
    return html, filename


def render_html_template(data: Dict[str, Any]) -> str:
    """Render the HTML report template."""
    
    severity_colors = {
        "CRITICAL": "#dc2626",
        "HIGH": "#ea580c",
        "MEDIUM": "#ca8a04",
        "LOW": "#16a34a",
        "INFO": "#2563eb"
    }
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeScan Report - {data['name']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; background: #f9fafb; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .header {{ background: white; border-radius: 8px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .header h1 {{ font-size: 1.875rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem; }}
        .header .meta {{ color: #6b7280; font-size: 0.875rem; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .summary-card {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .summary-card .value {{ font-size: 2rem; font-weight: 700; color: #111827; }}
        .summary-card .label {{ color: #6b7280; font-size: 0.875rem; }}
        .stage {{ background: white; border-radius: 8px; margin-bottom: 1.5rem; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .stage-header {{ padding: 1rem 1.5rem; border-bottom: 1px solid #e5e7eb; }}
        .stage-header h2 {{ font-size: 1.25rem; font-weight: 600; }}
        .stage-body {{ padding: 1.5rem; }}
        .finding {{ border-left: 4px solid; padding: 1rem; margin-bottom: 1rem; background: #f9fafb; border-radius: 0 4px 4px 0; }}
        .finding-title {{ font-weight: 600; margin-bottom: 0.5rem; }}
        .finding-meta {{ font-size: 0.875rem; color: #6b7280; margin-bottom: 0.5rem; }}
        .finding-desc {{ margin-bottom: 0.5rem; }}
        .finding-code {{ background: #1f2937; color: #f3f4f6; padding: 0.75rem; border-radius: 4px; font-family: monospace; font-size: 0.875rem; overflow-x: auto; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CodeScan Security Report</h1>
            <div class="meta">
                <p><strong>Project:</strong> {data['name']}</p>
                <p><strong>Generated:</strong> {data['generated_at']}</p>
                <p><strong>Task ID:</strong> {data['short_id']}</p>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="value">{data['summary']['total_findings']}</div>
                <div class="label">Total Findings</div>
            </div>
            <div class="summary-card">
                <div class="value">{data['summary']['completed_stage_count']}</div>
                <div class="label">Completed Stages</div>
            </div>
            <div class="summary-card">
                <div class="value">{data['summary']['clean_stage_count']}</div>
                <div class="label">Clean Stages</div>
            </div>
            <div class="summary-card">
                <div class="value">{data['summary']['unique_files']}</div>
                <div class="label">Files Analyzed</div>
            </div>
        </div>
"""
    
    for stage in data['stages']:
        accent_color = {
            "red": "#dc2626", "orange": "#ea580c", "blue": "#2563eb",
            "purple": "#7c3aed", "yellow": "#ca8a04", "green": "#16a34a",
            "teal": "#0d9488", "indigo": "#4f46e5", "gray": "#6b7280"
        }.get(stage['accent'], "#6b7280")
        
        html += f"""
        <div class="stage">
            <div class="stage-header" style="border-left: 4px solid {accent_color};">
                <h2>{stage['name']}</h2>
                <p style="color: #6b7280; font-size: 0.875rem;">{stage['description']}</p>
                <p style="margin-top: 0.5rem;"><span class="badge" style="background: {accent_color};">{stage['finding_count']} findings</span></p>
            </div>
            <div class="stage-body">
"""
        
        for finding in stage['findings']:
            color = severity_colors.get(finding['severity'], "#6b7280")
            html += f"""
                <div class="finding" style="border-color: {color};">
                    <div class="finding-title">
                        <span class="badge" style="background: {color};">{finding['severity']}</span>
                        {finding['title']}
                    </div>
                    <div class="finding-meta">
                        {finding['file']}:{finding['line']}
                    </div>
                    <div class="finding-desc">{finding['description']}</div>
"""
            if finding.get('evidence'):
                html += f'<div class="finding-code">{finding["evidence"]}</div>'
            if finding.get('recommendation'):
                html += f'<div style="margin-top: 0.5rem; font-style: italic;"><strong>Recommendation:</strong> {finding["recommendation"]}</div>'
            
            html += """
                </div>
"""
        
        if not stage['findings']:
            html += '<p style="color: #6b7280;">No issues found in this stage.</p>'
        
        html += """
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    return html
