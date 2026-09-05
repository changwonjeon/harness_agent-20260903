교육명: 하네스 엔지니어링 기반 프로덕션 수준 에이전트 개발
영문명: Harness Engineering & Production Agent Practice Course
교육 형태: 사내교육 및 실습 중심의 2일 과정
날짜: 2026년 9월 3일(목) ~ 4일(금), 2일간
시간: 매일 9am ~ 5pm
장소: 13동 L10
강사: 김형욱
강사 연락처: hukim@artiasolution.com
URL(강의자료): https://bit.ly/LGCNS-HARNESS
URL(GitHub): https://github.com/hukim1112/harness_agent

- 비결정적인 LLM을 신뢰할 수 있고 통제 가능한 비즈니스 프로세스로 전환하기 위한 프로덕션 AI 에이전트 하네스 엔지니어링 과정임
- 단순한 LLM 호출이나 챗봇 구현을 넘어 모델의 추론과 도구 실행을 조율하는 방법을 다룸
- 상태, 메모리, 권한, 평가, 보안, 관측성을 결합한 엔터프라이즈급 에이전트 아키텍처를 직접 구현하고 검증함

- 하네스 엔지니어링과 Agentic AI의 기본 개념을 학습함
  - Model과 Harness의 역할 및 차이를 이해함
  - Tool Use와 ReAct를 중심으로 에이전트의 기본 실행 구조를 살펴봄

- 추론 방식과 멀티에이전트 설계를 학습함
  - Tool Use, Reflection, Planning, Self-Recovery 패턴을 다룸
  - 단일 에이전트와 멀티에이전트 구조의 특징 및 선택 기준을 비교함
  - Supervisor-Worker와 Agent-as-Tool 기반 오케스트레이션 구조를 학습함

- 컨텍스트 엔지니어링과 메모리 아키텍처를 학습함
  - Claude Code 방식의 5-Layer 프롬프트 조립 구조를 다룸
  - Semantic Memory와 Episodic Memory의 역할 및 차이를 살펴봄
  - 2-Stage JIT 회상과 필요한 정보만 동적으로 불러오는 방식을 실습함
  - 컨텍스트 컴팩션과 장기 작업 중 기억 상실을 방지하는 구조를 학습함

- 도구 엔지니어링과 커스텀 MCP 구축을 실습함
  - 에이전트-컴퓨터 인터페이스 설계 원칙을 살펴봄
  - Progressive Skills와 동적 도구 발견 방식을 학습함
  - Static 및 Dynamic MCP 바인딩 구조를 비교함
  - FastMCP를 활용해 커스텀 MCP 서버와 도구를 구축함

- AI Agent 평가 체계와 신뢰성 엔지니어링을 학습함
  - LLM-as-a-Judge와 구조화된 평가 스키마를 다룸
  - 회귀 테스트와 평가 주도 개발 방식을 실습함
  - 런타임 자가 교정과 프롬프트 최적화 과정을 살펴봄
  - 최종 결과물뿐만 아니라 행동 궤적과 운영 성능을 함께 평가함

- 운영 거버넌스, 권한 통제 및 모니터링을 학습함
  - Human-in-the-Loop와 Allow·Ask·Deny 권한 정책을 다룸
  - 도구 실행의 승인, 수정, 거절 및 중단 지점부터의 실행 재개를 실습함
  - 입력 보안 가드레일과 무한 루프 제어 방식을 학습함
  - 감사 로깅, 실행 추적 및 운영 모니터링 구조를 구현함

- Python 3.12, LangChain, LangGraph, FastAPI, Chainlit을 중심으로 실습함
- GitHub 계정과 GitHub Codespaces를 사용해 실습환경을 구성함
- harness_agent 저장소의 단계별 Jupyter Notebook을 통해 주요 개념을 학습함
- 노트북 학습 후 프로덕션 미션을 순차적으로 수행함
- 커스텀 도구, 자가 복구, 서브에이전트, 프롬프트, 메모리, Skills, MCP, 권한 게이트, 가드레일, 로깅 및 관측성을 하나의 에이전트 시스템으로 통합함
- 과정 마지막에는 전체 구성 요소를 연결한 최종 통합 테스트를 수행함
- OpenAI 또는 Gemini API 사용을 위한 환경변수 설정이 필요함
- 실제 API 키와 기타 비밀정보는 교육 기록에 포함하지 않음