# 로컬 작업과 원본 저장소 업데이트를 안전하게 합치는 Git 튜토리얼

작성일은 2026년 9월 4일이며, `harness_agent` 저장소에서 실제로 수행한 작업을 학습용으로 재구성했다.

이 문서는 Git의 기본 개념은 알지만, 포크한 저장소에서 원본 변경과 커밋하지 않은 로컬 작업을 어떻게 안전하게 합쳐야 하는지 익히려는 사람을 대상으로 한다.

## 1. 이번 작업에서 해결하려던 문제

작업을 시작했을 때 세 가지 상태가 동시에 존재했다.

1. 로컬 `main`에는 전날 수정했지만 아직 커밋하지 않은 파일이 7개 있었다.
2. 내 GitHub 포크인 `origin/main`은 로컬 `main`과 같은 커밋을 가리키고 있었다.
3. 포크해 온 원본 저장소의 `upstream/main`에는 새로운 커밋 2개가 있었다.

목표는 어느 쪽의 변경도 잃지 않고 다음 상태를 만드는 것이었다.

```text
원본 저장소의 최신 커밋
          +
전날 작성한 로컬 변경
          ↓
통합된 로컬 main 브랜치
```

그다음 통합된 로컬 작업을 커밋하고 내 GitHub 포크의 `origin/main`으로 푸시했다.

## 2. 먼저 알아야 할 Git 구성요소

### 로컬 저장소와 작업 트리

로컬 저장소는 `.git` 디렉터리에 저장된 커밋 이력이다. 작업 트리는 편집기에서 실제로 보고 수정하는 파일들이다.

커밋하지 않은 수정은 작업 트리에만 존재한다. GitHub에는 올라가 있지 않으며, 브랜치를 변경하거나 병합할 때 충돌할 수 있다.

### `main`

`main`은 현재 로컬에서 작업하는 브랜치다. 브랜치는 특정 커밋을 가리키는 이동 가능한 이름이라고 이해하면 된다.

### `origin`

`origin`은 일반적으로 내가 복제한 GitHub 저장소를 가리킨다. 이번 사례에서는 사용자의 포크 저장소였다.

```text
origin = https://github.com/changwonjeon/harness_agent-20260903.git
```

### `upstream`

`upstream`은 포크의 원본 저장소를 가리키도록 추가한 리모트 이름이다.

```text
upstream = https://github.com/hukim1112/harness_agent.git
```

정리하면 `origin`은 내 GitHub 저장소이고, `upstream`은 변경을 받아올 원본 GitHub 저장소다.

### 작업 영역, 스테이징 영역, 커밋

Git 파일은 보통 다음 단계를 거친다.

```text
작업 영역에서 파일 수정
        │
        │ git add
        ▼
스테이징 영역
        │
        │ git commit
        ▼
로컬 커밋 이력
        │
        │ git push
        ▼
GitHub 원격 저장소
```

### stash

stash는 커밋하지 않은 작업을 임시 보관하는 공간이다. 아직 커밋으로 만들고 싶지 않은 변경을 잠시 치운 뒤 브랜치 작업을 해야 할 때 유용하다.

## 3. 1단계로 현재 상태부터 조사한 이유

Git 작업에서 가장 중요한 습관은 명령부터 실행하지 않고 현재 상태를 먼저 읽는 것이다.

이번에는 다음 명령을 사용했다.

```bash
git status --short --branch
git remote -v
git branch -vv
```

각 명령으로 알 수 있는 내용은 다음과 같다.

| 명령 | 확인하는 내용 |
|---|---|
| `git status --short --branch` | 현재 브랜치, 수정 파일, 원격보다 앞서거나 뒤처진 상태 |
| `git remote -v` | `origin`과 `upstream`이 가리키는 실제 주소 |
| `git branch -vv` | 현재 브랜치와 추적 중인 원격 브랜치 |

실제 확인 결과는 다음과 같은 의미였다.

```text
## main...origin/main
 M app/agents/chatbot.py
 M app/agents/main_agent.py
 M app/server.py
 M app/tools/custom_tools.py
 M artifacts/notebooks/cafe_generated/consumer_preference_report.md
 M install/requirements.txt
 M notebooks/1.Reasoning and Subagent.ipynb
```

첫 줄의 `main...origin/main` 뒤에 `ahead`나 `behind`가 없으므로 로컬 `main`과 `origin/main`은 같은 커밋을 가리키고 있었다.

파일 앞의 `M`은 해당 파일이 마지막 커밋 이후 수정됐다는 뜻이다. 이 7개 파일은 사용자의 작업이므로 삭제하거나 원본 파일로 덮어쓰면 안 됐다.

## 4. 바로 pull하지 않은 이유

이 상황에서 무작정 다음 명령을 실행할 수도 있다.

```bash
git pull upstream main
```

하지만 `git pull`은 다운로드와 병합을 연속으로 수행한다.

```text
git pull ≈ git fetch + git merge
```

커밋하지 않은 변경이 있는 상태에서 실행하면 Git이 작업을 거부하거나, 병합 과정에서 충돌이 발생하거나, 어떤 단계에서 문제가 생겼는지 이해하기 어려울 수 있다.

따라서 이번 작업에서는 다음 원칙을 사용했다.

1. 로컬 변경을 먼저 안전하게 보관한다.
2. 원본 변경을 다운로드만 한다.
3. 브랜치 관계를 분석한다.
4. 안전한 방식으로 병합한다.
5. 로컬 변경을 다시 적용한다.

## 5. 2단계로 로컬 변경을 stash에 백업

다음 명령으로 로컬 작업을 임시 보관했다.

```bash
git stash push --include-untracked \
  -m "codex: upstream 통합 전 로컬 작업 백업"
```

옵션의 의미는 다음과 같다.

| 구성 | 의미 |
|---|---|
| `git stash push` | 현재 변경을 stash에 저장 |
| `--include-untracked` | 아직 Git이 추적하지 않는 새 파일도 함께 저장 |
| `-m` | 나중에 알아볼 수 있는 설명 추가 |

stash가 생성됐는지는 다음 명령으로 확인했다.

```bash
git stash list
```

실제 생성된 백업은 다음과 같았다.

```text
stash@{0}: On main: codex: upstream 통합 전 로컬 작업 백업
```

stash 전후를 그림으로 보면 다음과 같다.

```text
stash 전

main의 마지막 커밋
        └── 작업 트리의 로컬 수정 7개

stash 후

main의 마지막 커밋

stash@{0}
        └── 로컬 수정 7개와 추적하지 않던 새 파일
```

이제 작업 트리가 깨끗해져 원본 커밋을 안전하게 반영할 수 있었다.

## 6. 3단계로 upstream의 최신 커밋 가져오기

다음 명령을 실행했다.

```bash
git fetch upstream main --prune
```

`fetch`는 원격의 커밋과 브랜치 정보를 내려받지만 현재 `main`이나 작업 파일은 변경하지 않는다.

`--prune`은 원격에서 이미 삭제된 브랜치의 오래된 추적 정보를 정리한다. 이번 핵심 작업에는 필수 옵션은 아니지만 리모트 상태를 최신으로 유지하는 데 도움이 된다.

가져온 정보는 `upstream/main`이라는 원격 추적 브랜치에 반영됐다.

```text
fetch 전

main, origin/main
        ↓
     b9337be

fetch 후

main, origin/main
        ↓
     b9337be ─── 74322f4 ─── df37a89
                                  ↑
                            upstream/main
```

여기서 중요한 점은 `fetch`만으로는 로컬 `main`이 이동하지 않는다는 것이다.

## 7. 4단계로 두 브랜치의 관계 분석

다음 명령으로 어느 쪽에만 존재하는 커밋이 몇 개인지 확인했다.

```bash
git rev-list --left-right --count main...upstream/main
```

결과는 다음과 같았다.

```text
0    2
```

왼쪽 숫자 `0`은 로컬 `main`에만 있는 커밋이 없다는 뜻이다. 오른쪽 숫자 `2`는 `upstream/main`에만 있는 커밋이 2개라는 뜻이다.

즉, 두 브랜치가 서로 다른 방향으로 갈라진 상태가 아니었다.

```text
갈라지지 않은 상태

A ─── B ─── C
↑           ↑
main        upstream/main
```

이 상태에서는 `main`의 포인터를 `upstream/main` 위치로 앞으로 이동시키기만 하면 된다. 이것이 fast-forward다.

반대로 양쪽 모두 고유 커밋이 있다면 다음처럼 갈라진 상태다.

```text
        ┌── L1  main
A ─── B ┤
        └── U1  upstream/main
```

이 경우에는 일반 병합 커밋이나 rebase 같은 추가 판단이 필요하다.

추가로 다음 명령으로 실제 커밋 그래프와 변경 파일을 확인했다.

```bash
git log --oneline --decorate --graph --max-count=20 --all
git diff --stat main..upstream/main
git diff --name-status main..upstream/main
```

원본의 새 커밋은 다음 두 개였다.

```text
74322f4 docs: update tests/README.md with compaction suite and relative links
df37a89 feat: Mission 08 졸업 검증 + 미들웨어 레퍼런스 + 경로 정리
```

원본은 주로 `missions/`와 `tests/` 아래 파일을 변경했다. 로컬 작업은 주로 `app/`, `install/`, `notebooks/` 파일을 변경했다. 수정 영역이 크게 겹치지 않아 충돌 가능성이 낮다고 판단했다.

## 8. 5단계로 upstream을 fast-forward 병합

다음 명령으로 원본 변경을 로컬 `main`에 반영했다.

```bash
git merge --ff-only upstream/main
```

`--ff-only`는 fast-forward가 가능한 경우에만 병합하도록 제한한다. 브랜치가 예상과 다르게 갈라져 있다면 Git이 임의로 병합 커밋을 만들지 않고 작업을 중단한다.

이번에는 `main`에만 존재하는 커밋이 없었으므로 성공했다.

```text
병합 전

main
 ↓
b9337be ─── 74322f4 ─── df37a89
                            ↑
                      upstream/main

병합 후

b9337be ─── 74322f4 ─── df37a89
                            ↑
                    main, upstream/main
```

fast-forward는 새로운 병합 커밋을 만들지 않는다. 기존 커밋의 작성자와 메시지도 그대로 유지된다.

## 9. 6단계로 로컬 작업 다시 적용

원본 최신 상태가 된 `main` 위에 stash의 로컬 작업을 다시 적용했다.

```bash
git stash apply stash@{0}
```

이번에는 `git stash pop` 대신 `git stash apply`를 선택했다.

| 명령 | 적용 후 stash 상태 |
|---|---|
| `git stash apply` | stash를 유지 |
| `git stash pop` | 성공하면 stash를 삭제 |

작업이 완전히 검증되기 전까지 복구 지점을 유지하는 편이 안전하므로 `apply`를 사용했다.

적용 결과 파일 충돌은 발생하지 않았다. 원본 변경과 로컬 변경이 모두 작업 트리에 존재하는 상태가 됐다.

```text
b9337be
   │
74322f4  원본 커밋
   │
df37a89  원본 커밋
   │
   └── 작업 트리에 전날 로컬 수정이 적용된 상태
```

stash 백업은 현재도 `stash@{0}`에 남아 있다. 필요가 없어졌다고 확신할 때 다음 명령으로 개별 삭제할 수 있다.

```bash
git stash drop stash@{0}
```

`drop`은 복구하기 어려운 삭제 작업이므로 대상 stash를 다시 확인한 뒤 실행해야 한다.

## 10. 충돌이 발생했다면 해결하는 방법

이번 작업에서는 충돌이 없었지만 같은 파일의 같은 줄을 양쪽에서 수정했다면 충돌이 생길 수 있다.

충돌 파일에는 보통 다음 표시가 들어간다.

```text
[<<<<<<< Updated upstream]
원본 저장소에서 가져온 내용
[=======]
stash에 있던 로컬 내용
[>>>>>>> Stashed changes]
```

충돌 해결 순서는 다음과 같다.

1. `git status`로 충돌 파일을 확인한다.
2. 파일을 열어 원본 내용과 로컬 내용을 비교한다.
3. 최종적으로 유지할 내용을 직접 작성한다.
4. `<<<<<<<`, `=======`, `>>>>>>>` 표시를 모두 제거한다.
5. 해결한 파일을 `git add`로 스테이징한다.
6. 테스트를 실행한다.

예시는 다음과 같다.

```bash
git status
git diff --name-only --diff-filter=U

# 편집기에서 충돌을 해결한 뒤 실행
git add app/example.py
git diff --check
```

충돌 해결에서 중요한 점은 무조건 한쪽 전체를 선택하는 것이 아니라 두 변경의 의도를 이해하고 최종 결과를 만드는 것이다.

## 11. 7단계로 통합 결과 검증

Git이 충돌 없이 파일을 합쳤다고 해서 프로그램이 정상 동작한다는 뜻은 아니다. 문법 오류나 동작 문제가 있을 수 있으므로 테스트가 필요하다.

먼저 패치의 공백 문제를 확인했다.

```bash
git diff --check
```

기존 `app/tools/custom_tools.py` 수정에서 후행 공백 2건이 확인됐다. 이는 병합 충돌은 아니었으며 사용자 작업을 임의로 바꾸지 않고 기록만 남겼다.

로컬 작업과 직접 관련된 테스트를 실행했다.

```bash
.venv/bin/python tests/test_mission01.py
.venv/bin/python tests/test_mission02.py
```

두 테스트 모두 통과했다.

Python 문법과 노트북 JSON 구조도 확인했다.

```bash
.venv/bin/python -m compileall -q app tests
.venv/bin/python -m json.tool \
  "notebooks/1.Reasoning and Subagent.ipynb"
```

이 검사들도 통과했다.

새로 추가된 `tests/test_final.py`는 Gemini와 LangSmith에 접속해야 하는 통합 테스트였다. 실행 환경의 네트워크 제한으로 외부 호스트에 연결하지 못해 끝까지 완료하지 못했고, 그 제한을 작업 기록에 명시했다.

## 12. 8단계로 로컬 작업 커밋

검증 후 로컬 작업을 스테이징했다.

```bash
git add app/agents/chatbot.py \
  app/agents/main_agent.py \
  app/server.py \
  app/tools/custom_tools.py \
  artifacts/notebooks/cafe_generated/consumer_preference_report.md \
  install/requirements.txt \
  "notebooks/1.Reasoning and Subagent.ipynb" \
  checklist.md \
  context-notes.md
```

그다음 하나의 논리적인 커밋으로 저장했다.

```bash
git commit -m "feat: 로컬 실습 결과와 원본 업데이트 통합"
```

생성된 커밋은 다음과 같다.

```text
503f765 feat: 로컬 실습 결과와 원본 업데이트 통합
```

원본 커밋과 사용자의 커밋이 분리된 최종 구조는 다음과 같았다.

```text
b9337be  기존 공통 커밋
   │
74322f4  upstream 문서 업데이트
   │
df37a89  upstream Mission 08 업데이트
   │
503f765  사용자의 전날 로컬 작업
```

이 구조의 장점은 누가 어떤 변경을 작성했는지 커밋 단위로 확인할 수 있다는 것이다. 실제로 `74322f4`와 `df37a89`는 원본 작성자 `hukim`, `503f765`는 `Changwon`으로 기록됐다.

## 13. README와 비밀 파일 설정을 별도 커밋으로 관리

통합 후 macOS 로컬 실행 방법과 `.env` 보호 규칙도 수정했다. 이 작업은 앞선 기능 구현과 목적이 다르므로 별도 커밋으로 만들었다.

```bash
git commit -m "docs: macOS 로컬 환경과 비밀 파일 관리 안내"
```

생성된 커밋은 다음과 같다.

```text
2ae8e50 docs: macOS 로컬 환경과 비밀 파일 관리 안내
```

`.gitignore`에는 다음 원칙을 반영했다.

```gitignore
.env
.env.*
!.env.example
```

실제 비밀값이 들어가는 `.env`와 `.env.local` 같은 파일은 무시하고, 공개 템플릿인 `.env.example`만 Git으로 관리한다.

## 14. 9단계로 내 GitHub 포크에 push

로컬 커밋을 내 GitHub 포크의 `main`으로 전송했다.

```bash
git push origin main
```

여기서 `origin`에 푸시했다는 점이 중요하다. `upstream`은 원본 저장소이므로 권한과 목적을 확인하지 않은 상태에서 직접 푸시하면 안 된다.

푸시 후 다음 명령으로 로컬과 원격이 같은 커밋을 가리키는지 확인했다.

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

당시 `HEAD`와 `origin/main`은 모두 `2ae8e50`을 가리켰다.

```text
local main ─── 2ae8e50
origin/main ── 2ae8e50
```

## 15. 작업 전체 흐름

```text
현재 상태 조사
  git status, git remote, git branch
          │
          ▼
로컬 작업 백업
  git stash push --include-untracked
          │
          ▼
원본 변경 다운로드
  git fetch upstream main
          │
          ▼
브랜치 관계 분석
  git rev-list, git log, git diff
          │
          ▼
원본을 로컬 main에 반영
  git merge --ff-only upstream/main
          │
          ▼
로컬 작업 복원
  git stash apply stash@{0}
          │
          ▼
충돌 확인과 테스트
  git status, git diff --check, 프로젝트 테스트
          │
          ▼
로컬 작업 커밋
  git add, git commit
          │
          ▼
내 GitHub 포크에 전송
  git push origin main
```

## 16. 비슷한 상황에서 재사용할 수 있는 명령 순서

다음은 이번 패턴을 일반화한 예시다. 명령을 그대로 실행하기 전에 리모트 이름과 브랜치 이름이 자신의 저장소와 같은지 반드시 확인해야 한다.

```bash
# 1. 현재 상태와 리모트 확인
git status --short --branch
git remote -v
git branch -vv

# 2. 커밋하지 않은 작업 백업
git stash push --include-untracked -m "upstream 통합 전 백업"
git stash list

# 3. 원본 최신 정보 가져오기
git fetch upstream main --prune

# 4. 커밋 관계와 변경 파일 분석
git rev-list --left-right --count main...upstream/main
git log --oneline --decorate --graph --all --max-count=20
git diff --name-status main..upstream/main

# 5. fast-forward가 가능할 때만 반영
git merge --ff-only upstream/main

# 6. 로컬 작업 다시 적용
git stash apply stash@{0}

# 7. 충돌과 diff 검사
git status
git diff --check

# 8. 프로젝트 테스트 후 커밋
git add <검증한 파일들>
git commit -m "변경 목적을 설명하는 메시지"

# 9. 내 원격 저장소로 push
git push origin main

# 10. 최종 상태 확인
git status --short --branch
git log --oneline --decorate --graph --max-count=10
```

## 17. 자주 하는 실수와 예방 방법

### 수정 파일을 확인하지 않고 pull 실행

커밋하지 않은 작업이 있을 때 바로 `pull`하면 상황이 복잡해질 수 있다. 먼저 `git status`를 확인하고 작업을 커밋하거나 stash에 보관한다.

### origin과 upstream을 혼동

포크 저장소에서는 두 리모트의 역할이 다르다.

```text
upstream에서 가져오기
origin으로 푸시하기
```

항상 `git remote -v`로 실제 URL을 확인한다.

### stash에 새 파일이 빠지는 문제

기본 `git stash`는 추적하지 않는 새 파일을 포함하지 않을 수 있다. 새 파일까지 보관하려면 `--include-untracked`를 사용한다.

### 확인 없이 stash pop 사용

`stash pop`은 성공하면 stash를 삭제한다. 중요한 작업에서는 먼저 `stash apply`를 사용하고 검증이 끝난 뒤 명시적으로 삭제하는 편이 안전하다.

### 브랜치가 갈라졌는데 무조건 merge

`git rev-list --left-right --count`로 관계를 확인한다. fast-forward가 예상되는 작업에서는 `git merge --ff-only`를 사용하면 예상하지 않은 병합 커밋 생성을 막을 수 있다.

### 테스트 없이 커밋과 push

Git의 충돌 해결과 프로그램의 정상 동작은 별개다. 프로젝트에 맞는 테스트, 빌드 또는 문법 검사를 실행한 뒤 커밋한다.

### `.env`를 실수로 커밋

API 키가 포함된 `.env`는 반드시 `.gitignore`에서 제외한다. 이미 커밋한 적이 있다면 `.gitignore`만 추가해서는 과거 이력의 비밀값이 사라지지 않는다. 그 경우 키를 즉시 폐기하고 Git 이력 정리도 별도로 검토해야 한다.

## 18. 현재 저장소에서 이어진 후속 상태

README의 macOS Python 환경을 `venv + pip`에서 `uv` 기반으로 정정하는 후속 커밋도 만들었다.

```text
fc9be54 docs: macOS Python 환경을 uv 기반으로 정정
```

이 튜토리얼을 작성하기 직전 기준으로 `fc9be54`는 로컬 `main`에만 있고 `origin/main`에는 아직 푸시되지 않았다.

따라서 `git status --short --branch`는 다음 의미의 상태를 표시했다.

```text
main...origin/main [ahead 1]
```

`ahead 1`은 로컬에 원격보다 커밋이 하나 더 있다는 뜻이다. 파일이 수정된 상태라는 뜻은 아니다.

## 19. 복습 질문

다음 질문에 답할 수 있다면 이번 작업의 핵심 개념을 이해한 것이다.

1. `origin`과 `upstream`은 어떤 차이가 있는가.
2. `git fetch`와 `git pull`은 어떤 차이가 있는가.
3. `git stash apply`와 `git stash pop`은 어떤 차이가 있는가.
4. `git rev-list --left-right --count main...upstream/main` 결과 `0 2`는 무엇을 의미하는가.
5. `git merge --ff-only`는 어떤 상황에서 성공하는가.
6. Git 충돌이 없더라도 테스트가 필요한 이유는 무엇인가.
7. `main...origin/main [ahead 1]`은 어떤 상태를 뜻하는가.

## 20. 핵심 원칙

이번 작업에서 가장 중요한 원칙은 다음과 같다.

```text
상태를 먼저 확인한다.
로컬 작업을 먼저 보호한다.
다운로드와 병합을 분리한다.
브랜치 관계를 확인하고 병합 방식을 선택한다.
stash를 다시 적용한 뒤 반드시 검증한다.
원본 커밋과 내 작업 커밋을 구분해서 남긴다.
push할 리모트가 origin인지 upstream인지 확인한다.
```

이 순서를 습관으로 만들면 포크 저장소의 원본 업데이트와 로컬 작업을 훨씬 안전하게 관리할 수 있다.
