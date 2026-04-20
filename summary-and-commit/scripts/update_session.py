#!/usr/bin/env python3
"""
Update SESSION.md with session summary and manage session history.
- Keep up to 40 session summaries
- Show full details for last 5 sessions
- Older sessions show one-line summary (like changelog)

Usage:
    python update_session.py "Session summary text"
    echo "Session summary text" | python update_session.py
"""
import sys
import re
from datetime import datetime
from pathlib import Path


def update_session_history(summary_text: str, filepath: str = 'SESSION.md') -> tuple[int, int]:
    """Update SESSION.md with new session, maintaining retention rules."""
    filepath = Path(filepath)
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Parse existing sessions
    sessions = []
    if filepath.exists():
        content = filepath.read_text(encoding='utf-8')
        # Pattern for detailed sessions
        session_pattern = r'### Session (\d+) - (\d{4}-\d{2}-\d{2})\n\n((?:(?!### Session)[\s\S])+)'
        for match in re.finditer(session_pattern, content):
            sessions.append({
                'number': int(match.group(1)),
                'date': match.group(2),
                'details': match.group(3).strip(),
                'is_detailed': True
            })
        # Pattern for brief sessions
        brief_pattern = r'- \*\*Session (\d+)\*\* \((\d{4}-\d{2}-\d{2})\): (.+?)(?=\n- \*\*Session|\n\n---|\Z)'
        for match in re.finditer(brief_pattern, content, re.DOTALL):
            sessions.append({
                'number': int(match.group(1)),
                'date': match.group(2),
                'details': match.group(3).strip(),
                'is_detailed': False
            })
        sessions.sort(key=lambda x: x['number'], reverse=True)
    
    # Create new session
    next_num = max([s['number'] for s in sessions], default=0) + 1
    sessions.insert(0, {
        'number': next_num,
        'date': current_date,
        'details': summary_text.strip(),
        'is_detailed': True
    })
    
    # Build new content
    detailed = [s for s in sessions if s['is_detailed']][:5]
    brief = [s for s in sessions if not s['is_detailed']]
    
    # Convert older detailed sessions to brief
    for s in sessions[5:]:
        if s['is_detailed']:
            # Take first line, remove bullet, limit to 60 chars
            first_line = s['details'].split('\n')[0].lstrip('- ').strip()
            brief_summary = first_line[:57] + '...' if len(first_line) > 60 else first_line
            brief.append({
                'number': s['number'],
                'date': s['date'],
                'details': brief_summary,
                'is_detailed': False
            })
        else:
            brief.append(s)
    
    brief.sort(key=lambda x: x['number'], reverse=True)
    brief = brief[:40 - len(detailed)]
    
    # Build file content
    lines = [
        '# Session History',
        '',
        '> 开发会话历史记录 | Development Session History',
        '>',
        '> 由 summary-and-commit skill 自动生成和更新',
        '> Auto-generated and updated by summary-and-commit skill',
        '',
        '---',
        '',
        '## Recent Sessions (最近5次)',
        ''
    ]
    
    for s in detailed:
        lines.append(f'### Session {s["number"]} - {s["date"]}')
        lines.append('')
        lines.append(s['details'])
        lines.append('')
    
    if brief:
        lines.append('## Earlier Sessions (历史会话)')
        lines.append('')
        for s in brief:
            lines.append(f'- **Session {s["number"]}** ({s["date"]}): {s["details"]}')
        lines.append('')
    
    lines.append('---')
    lines.append('')
    total = len(detailed) + len(brief)
    lines.append(f'*Total: {total} sessions | Last Updated: {current_date}*')
    lines.append('')
    
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    return next_num, total


if __name__ == '__main__':
    # Read summary from command line or stdin
    if len(sys.argv) > 1:
        summary = sys.argv[1]
    else:
        summary = sys.stdin.read()
    
    if not summary.strip():
        print("Error: No summary provided", file=sys.stderr)
        print("Usage: python update_session.py 'Session summary text'", file=sys.stderr)
        sys.exit(1)
    
    filepath = sys.argv[2] if len(sys.argv) > 2 else 'SESSION.md'
    num, total = update_session_history(summary, filepath)
    print(f'[OK] SESSION.md updated: Session {num} added (Total: {total})')
