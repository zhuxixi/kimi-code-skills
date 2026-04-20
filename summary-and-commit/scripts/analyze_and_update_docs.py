#!/usr/bin/env python3
"""
Analyze session summary and update AGENTS.md/CLAUDE.md if necessary.

This script:
1. Analyzes the session summary for important updates
2. Checks if AGENTS.md or CLAUDE.md need content updates
3. Updates Last Updated timestamp
4. Provides recommendations for manual updates

Usage:
    python analyze_and_update_docs.py "session_summary" [filepath]
"""
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


# Keywords that indicate important changes requiring doc updates
IMPORTANT_KEYWORDS = [
    # 架构和设计
    '架构', '设计', '重构', '结构', '分层', '模块', '组件',
    'architecture', 'design', 'refactor', 'structure', 'layer', 'module', 'component',
    
    # 技术栈
    '技术栈', '框架', '库', '依赖', '版本',
    'stack', 'framework', 'library', 'dependency', 'version',
    
    # 开发规范
    '规范', '约定', '标准', '风格', '规则', '指南',
    'convention', 'standard', 'style', 'rule', 'guideline',
    
    # 工作流程
    '流程', '工作流', 'CI/CD', '部署', '构建', '测试',
    'workflow', 'pipeline', 'deploy', 'build', 'test',
    
    # 重要决策
    '决策', '决定', '方案', '选型', '变更', '调整',
    'decision', 'solution', 'selection', 'change', 'adjustment',
    
    # 安全
    '安全', '认证', '授权', '加密', '漏洞',
    'security', 'auth', 'encrypt', 'vulnerability',
    
    # 性能
    '性能', '优化', '缓存', '并发',
    'performance', 'optimize', 'cache', 'concurrency',
]


def analyze_summary(summary: str) -> Tuple[bool, List[str], str]:
    """
    Analyze session summary for important content.
    
    Returns:
        (has_important_content, matched_keywords, recommendation)
    """
    summary_lower = summary.lower()
    matched = []
    
    for keyword in IMPORTANT_KEYWORDS:
        if keyword.lower() in summary_lower:
            matched.append(keyword)
    
    has_important = len(matched) > 0
    
    if has_important:
        recommendation = (
            f"检测到可能涉及文档更新的内容（关键词: {', '.join(matched[:5])}...）。\n"
            "建议检查 AGENTS.md/CLAUDE.md 是否需要更新相关章节。"
        )
    else:
        recommendation = "本次会话内容主要为代码实现，无需更新项目文档。"
    
    return has_important, matched, recommendation


def update_timestamp(filepath: str) -> bool:
    """Update Last Updated timestamp in the specified file."""
    path = Path(filepath)
    
    if not path.exists():
        return False
    
    try:
        content = path.read_text(encoding='utf-8')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Pattern to match Last Updated date
        date_pattern = r'(\*?\*?Last Updated[:\s]+)\d{4}-\d{2}-\d{2}(\*?\*?)'
        
        if re.search(date_pattern, content, re.IGNORECASE):
            updated_content = re.sub(
                date_pattern, 
                rf'\g<1>{today}\g<2>', 
                content, 
                flags=re.IGNORECASE
            )
            path.write_text(updated_content, encoding='utf-8')
            return True
        return False
            
    except Exception:
        return False


def check_doc_references(filepath: str) -> bool:
    """Check if file references SESSION.md."""
    path = Path(filepath)
    
    if not path.exists():
        return False
    
    try:
        content = path.read_text(encoding='utf-8')
        return 'SESSION.md' in content or 'session history' in content.lower()
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_and_update_docs.py 'session_summary' [filepath]", file=sys.stderr)
        sys.exit(1)
    
    summary = sys.argv[1]
    target_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Analyze summary
    has_important, matched, recommendation = analyze_summary(summary)
    
    # Determine which files to process
    files_to_process = []
    if target_file:
        files_to_process.append(target_file)
    else:
        # Check both AGENTS.md and CLAUDE.md in current directory
        for filename in ['AGENTS.md', 'CLAUDE.md']:
            if Path(filename).exists():
                files_to_process.append(filename)
    
    # Process each file
    updated_files = []
    session_refs = []
    
    for filepath in files_to_process:
        # Update timestamp
        if update_timestamp(filepath):
            updated_files.append(filepath)
        
        # Check SESSION.md reference
        if check_doc_references(filepath):
            session_refs.append(filepath)
    
    # Output results
    print("=" * 50)
    print("文档分析结果")
    print("=" * 50)
    print(f"\n{recommendation}")
    
    if matched:
        print(f"\n匹配关键词: {', '.join(matched)}")
    
    print(f"\n时间戳已更新: {', '.join(updated_files) if updated_files else '无'}")
    print(f"包含会话引用: {', '.join(session_refs) if session_refs else '无'}")
    
    if has_important and updated_files:
        print("\n⚠️  提示: 本次会话包含重要变更，请考虑手动更新上述文档的内容。")
    
    print("=" * 50)


if __name__ == '__main__':
    main()
