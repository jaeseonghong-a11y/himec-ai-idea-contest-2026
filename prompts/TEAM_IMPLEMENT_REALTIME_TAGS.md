# 팀원 AI에게 붙여 넣는 요청문 — 실시간 음성 객체 태그 한 작업 구현

아래 내용을 그대로 팀원 AI에게 붙여 넣고, 대괄호만 채우면 된다.

```text
이 저장소에서 실시간 음성 객체 태그 계획의 한 작업만 구현해줘.

내 GitHub 사용자명은 [내 GitHub 사용자명]이고, 팀장이 배정한 작업 브랜치는 [work/사용자명/rNN]이야.
이번에 맡은 작업은 [RT-01 / RT-02 / RT-03 / RT-04]이고, 그 밖의 기능은 구현하거나 건드리지 마.

먼저 AGENTS.md, START_HERE.md, BRANCH_ASSIGNMENTS.md, CURRENT_STATE.md,
docs/REALTIME_SPEECH_OBJECT_TAGGING_PLAN.md, sources/SRC-006_OPENAI_REALTIME_TRANSCRIPTION.md를 읽어줘.

반드시 다음을 지켜줘.
1. 내 배정 브랜치만 사용하고 main에는 commit, push, merge, rebase, reset을 하지 마.
2. 계획 문서의 해당 RT 작업에 지정된 파일 범위만 수정해. 공통 UI 파일을 다른 RT 작업과 섞지 마.
3. API 키·토큰·실제 음성·도면 파일·개인정보를 코드, Git, 로그, PR 본문에 넣지 마.
4. 실제 OpenAI API 호출은 하지 말고 가짜 전송기와 자동 테스트로만 검증해. 실제 마이크/API 검증은 통합 담당자가 한다.
5. 실시간 결과가 도면을 자동으로 수정하거나, 사람 확인 전에 확정 태그가 되게 만들지 마.
6. 작업 전후 git status와 diff를 확인하고, 내 담당 파일만 stage해서 feat:/fix:/test:/docs: 형식의 커밋을 만들어 push해.
7. main 대상 PR을 열고, PR 본문에는 바꾼 파일, 실행한 검증과 결과, 미검증 사항, 다른 RT 작업과 겹치지 않는 범위를 적은 뒤 멈춰. PR을 직접 병합하지 마.

완료 기준은 계획 문서의 [RT-작업번호] 행과 6절 검증표를 그대로 따라줘.
```

## 팀장이 먼저 채워야 할 것

- `RT-01`~`RT-04` 중 하나만 선택한다.
- 최신 `main`에서 해당 팀원 전용 `work/<github-user>/rNN` 브랜치를 만든다.
- `BRANCH_ASSIGNMENTS.md`에 담당 이슈·브랜치·수정 가능 파일을 기록한다.
- 같은 파일을 두 작업에 동시에 주지 않는다. 특히 `ReviewPanel.cs`, `RecordingTagPanel.cs`, `Himec.ChangeCore.Tests/Program.cs`는 계획 문서의 지정 작업 외에는 맡기지 않는다.

통합·실제 API·실제 AutoCAD 테스트·릴리스는 팀원이 아니라 `jaeseonghong-a11y`와 통합 담당 AI가 수행한다.
