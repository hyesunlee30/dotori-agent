#!/usr/bin/env python3
"""
dotori-agent - 레거시 현대화 엔진

사용법:
    python main.py workflow          # 워크플로우 파이프라인 실행
    python main.py agent             # AI 에이전트 실행 (자가수정 포함)
    python main.py compare           # 두 트랙 비교 실행
    python main.py --help            # 도움말

출력 위치:
    converted/workflow/  - 워크플로우 결과
    converted/agent/     - 에이전트 결과
"""

import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotori.workflows.pipeline import run_workflow_pipeline
from dotori.agent.graph import ConversionAgent, ModuleType
from dotori.runners.compare import run_both_tracks


LEGACY_DIR = ROOT / "legacy"
TARGET_DIR = ROOT / "converted"


def run_workflow():
    """워크플로우 파이프라인 실행"""
    print("=" * 60)
    print("  WORKFLOW PIPELINE 실행 중...")
    print("=" * 60)
    
    result = run_workflow_pipeline(
        legacy_dir=LEGACY_DIR,
        target_dir=TARGET_DIR / "workflow",
    )
    
    print(f"\n결과: {result.status.value}")
    print(f"에러: {len(result.errors)}개")
    for err in result.errors[:5]:
        print(f"  - {err}")
    
    print(f"\n출력: {TARGET_DIR / 'workflow'}")


def run_agent():
    """AI 에이전트 실행 (자가수정 루프 포함)"""
    print("=" * 60)
    print("  AGENT PIPELINE 실행 중...")
    print("=" * 60)
    
    agent = ConversionAgent(
        legacy_backend_dir=LEGACY_DIR / "backend-api",
        legacy_frontend_dir=LEGACY_DIR / "frontend-ui",
        target_dir=TARGET_DIR / "agent",
    )
    
    results = agent.convert_all(output_base=TARGET_DIR / "agent")
    
    for module, result in results.items():
        status = "성공" if result["success"] else "실패"
        retries = result.get("retry_count", 0)
        print(f"\n[{module}] {status} (재시도: {retries}회)")
        if result.get("error"):
            print(f"  에러: {result['error'][:200]}")
    
    print(f"\n출력: {TARGET_DIR / 'agent'}")


def run_compare():
    """두 트랙 비교 실행"""
    print("=" * 60)
    print("  WORKFLOW vs AGENT 비교 실행 중...")
    print("=" * 60)
    
    track_result = run_both_tracks(
        legacy_dir=LEGACY_DIR,
        target_dir=TARGET_DIR,
    )
    
    track_result.print_comparison()
    print(f"\n출력:")
    print(f"  워크플로우: {TARGET_DIR / 'workflow'}")
    print(f"  에이전트:   {TARGET_DIR / 'agent'}")


def main():
    parser = argparse.ArgumentParser(
        description="dotori-agent - 레거시 현대화 엔진",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py workflow     # 워크플로우 파이프라인 실행
  python main.py agent        # AI 에이전트 실행
  python main.py compare      # 두 트랙 비교
        """,
    )
    
    parser.add_argument(
        "command",
        choices=["workflow", "agent", "compare"],
        help="실행 모드: workflow, agent, compare",
    )
    
    args = parser.parse_args()
    
    if args.command == "workflow":
        run_workflow()
    elif args.command == "agent":
        run_agent()
    elif args.command == "compare":
        run_compare()


if __name__ == "__main__":
    main()