#!/usr/bin/env python3
"""
dotori-agent 테스트 실행 스크립트

legacy 폴더의 코드를 converted 폴더로 변환하고,
워크플로우(선형) 트랙과 에이전트(자가수정) 트랙 결과를 비교합니다.

Usage:
    python run_test.py
"""

import sys
import time
import json
import shutil
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotori.workflows.pipeline import run_workflow_pipeline
from dotori.agent.graph import ConversionAgent, ModuleType
from dotori.runners.compare import TrackResult


LEGACY_DIR = ROOT / "legacy"
TARGET_DIR = ROOT / "converted"


def clear_converted():
    """converted 폴더 초기화"""
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    (TARGET_DIR / "backend").mkdir(parents=True, exist_ok=True)
    (TARGET_DIR / "frontend").mkdir(parents=True, exist_ok=True)
    print(f"[init] converted 폴더 초기화: {TARGET_DIR}")


def run_workflow_track() -> tuple:
    """Track 1: 워크플로우 파이프라인 실행 (선형, 자가수정 없음)"""
    print("\n" + "=" * 60)
    print("[TRACK 1] WORKFLOW PIPELINE (선형 처리)")
    print("=" * 60)

    start = time.time()
    result = run_workflow_pipeline(
        legacy_dir=LEGACY_DIR,
        target_dir=TARGET_DIR / "workflow",
    )
    duration = time.time() - start

    print(f"\n  상태: {result.status.value}")
    print(f"  소요시간: {duration:.1f}초")
    print(f"  에러 수: {len(result.errors)}")
    for err in result.errors[:5]:
        print(f"    - {err}")

    # converted 파일 확인
    wf_dir = TARGET_DIR / "workflow"
    files = list(wf_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    print(f"\n  생성된 파일 수: {len(files)}")
    for f in sorted(files)[:20]:
        print(f"    + {f.relative_to(TARGET_DIR)}")
    if len(files) > 20:
        print(f"    ... 그리고 {len(files) - 20}개 파일 더")

    return result, duration


def run_agent_track() -> tuple:
    """Track 2: AI 에이전트 실행 (자가수정 루프 포함)"""
    print("\n" + "=" * 60)
    print("[TRACK 2] AGENT PIPELINE (자가수정 루프)")
    print("=" * 60)

    start = time.time()
    agent = ConversionAgent(
        legacy_backend_dir=LEGACY_DIR / "backend-api",
        legacy_frontend_dir=LEGACY_DIR / "frontend-ui",
        target_dir=TARGET_DIR / "agent",
    )
    results = agent.convert_all()
    duration = time.time() - start

    for module, result in results.items():
        print(f"\n  [{module}]")
        print(f"    상태: {result['status']}")
        print(f"    성공: {result['success']}")
        print(f"    재시도: {result.get('retry_count', 'N/A')}회")
        if result.get('error'):
            print(f"    에러: {result['error'][:200]}")

    # converted 파일 확인
    agent_dir = TARGET_DIR / "agent"
    files = list(agent_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    print(f"\n  생성된 파일 수: {len(files)}")
    for f in sorted(files)[:20]:
        print(f"    + {f.relative_to(TARGET_DIR)}")
    if len(files) > 20:
        print(f"    ... 그리고 {len(files) - 20}개 파일 더")

    return results, duration


def print_comparison(wf_result, wf_duration, agent_results, agent_duration):
    """두 트랙 결과를 비교하여 출력"""
    print("\n" + "=" * 70)
    print("  WORKFLOW vs AGENT - 비교 결과")
    print("=" * 70)

    # 워크플로우 요약
    wf_files = list((TARGET_DIR / "workflow").rglob("*"))
    wf_files = [f for f in wf_files if f.is_file()]

    print(f"\n  {'구분':<20} {'워크플로우':<25} {'에이전트'}")
    print(f"  {'-'*20} {'-'*25} {'-'*25}")
    print(f"  {'상태':<20} {wf_result.status.value:<25} {'-'*25}")

    for module, result in agent_results.items():
        agent_status = "success" if result['success'] else "failed"
        agent_retries = f"{result['retry_count']}회"
        print(f"  [{module:<14}] {'-'*15} {agent_status:<10} ({agent_retries})")

    print(f"  {'소요시간':<20} {wf_duration:.1f}초{'':<15} {agent_duration:.1f}초")

    agent_files = list((TARGET_DIR / "agent").rglob("*"))
    agent_files = [f for f in agent_files if f.is_file()]
    print(f"  {'생성된 파일':<20} {len(wf_files)}개{'':<15} {len(agent_files)}개")

    # 핵심 차이점
    print(f"\n  [핵심 차이점]")
    print(f"    워크플로우:  고정 DAG 순서, 재시도 없음, LLM 2회 호출")
    print(f"    에이전트:   validate -> self_reflect -> correct 루프, 최대 3회 재시도")
    print(f"    워크플로우:  빠름, 비용 낮음, 표준 변환 품질")
    print(f"    에이전트:    느림, 비용 높음, 에러 분석 후 적응형 개선")

    print("\n" + "=" * 70)


def print_output_summary():
    """최종 출력 파일 구조 표시"""
    print("\n" + "=" * 60)
    print("  최종 출력 파일 구조 (converted/)")
    print("=" * 60)

    for track in ["workflow", "agent"]:
        track_dir = TARGET_DIR / track
        if not track_dir.exists():
            print(f"\n  [{track}] 폴더 없음")
            continue

        print(f"\n  [converted/{track}/]")
        for root, dirs, files in sorted(os.walk(track_dir)):
            level = root.replace(str(track_dir), '').count(os.sep)
            indent = '    ' * level
            print(f'{indent}{os.path.basename(root)}/')
            sub_indent = '    ' * (level + 1)
            for file in sorted(files)[:10]:
                print(f'{sub_indent}{file}')
            if len(files) > 10:
                print(f'{sub_indent}... 그리고 {len(files) - 10}개 파일 더')


def main():
    print("=" * 60)
    print("  dotori-agent 테스트 실행")
    print("=" * 60)
    print(f"\n  레거시 소스: {LEGACY_DIR}")
    print(f"  변환 결과:   {TARGET_DIR}")
    print(f"  백엔드:      {LEGACY_DIR / 'backend-api'}")
    print(f"  프론트엔드:  {LEGACY_DIR / 'frontend-ui'}")

    # converted 폴더 초기화
    clear_converted()

    # Track 1: 워크플로우
    wf_result, wf_duration = run_workflow_track()

    # Track 2: 에이전트
    agent_results, agent_duration = run_agent_track()

    # 비교 결과 출력
    print_comparison(wf_result, wf_duration, agent_results, agent_duration)

    # 최종 출력 구조
    print_output_summary()

    print("\n[완료] converted 폴더에서 결과 확인하세요.")
    print(f"  워크플로우: {TARGET_DIR / 'workflow'}")
    print(f"  에이전트:   {TARGET_DIR / 'agent'}")


if __name__ == "__main__":
    import os
    main()