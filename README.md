# dotori-engine

![img.png](img.png)

> **"레거시 도토리를 모아 신뢰할 수 있는 차세대 시스템으로 가공하는 자동화 마이그레이션 제품"**
> **dotori-agent**는 복잡한 레거시 코드를 파악하고 명세서와 대조하여, 컴파일 및 테스트 검증까지 스스로 수행하는 **AI 기반 자가 수정(Self-Correction) 레거시 현대화 엔진**입니다.

### 가상 환경
1. 가상환경 생성 (.venv 폴더가 생깁니다)
python3 -m venv .venv

3. 가상환경 활성화 (macOS)
source .venv/bin/activate

### 패키지
1. 에이전트 구축용 필수 패키지 설치
pip install langgraph langchain-openai pymupdf python-dotenv
2. 설치된 패키지 목록 파일 생성
pip freeze > requirements.txt
3. dotori-engine 폴더 구조 만들기
mkdir -p dotori/parsers dotori/agent dotori/validators docs/performance