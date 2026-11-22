# 작업 지시: 벤치마크 엣지 블라인드 라벨링 (v3 라운드)

## 0. 시작 전 확인
- 이 세션은 이 파일의 지시만 받고 시작해야 합니다. 이 벤치마크의 실행 기록, 결과, 도구별
  집계, 이슈 내용 같은 다른 맥락을 이미 받았다면 **작업하지 말고** 그 사실만 보고하세요.
- 작업 도중 아래 허용 목록 밖의 내용을 보게 되면 거기서 멈추고 무엇을 봤는지 보고하세요.

## 1. 배경
`bench/`는 클래스 다이어그램을 그리는 세 가지 방법을 비교하는 벤치마크입니다. 같은 설정으로
세 번째 라운드를 실행했고, 그려진 엣지를 모아 중복을 없애고 섞었습니다. 앞 라운드들에서 이미
라벨이 붙은 엣지는 그 라벨을 가져왔고, **라벨이 비어 있는 88행이 이번 작업 대상**입니다.
각 엣지가 소스에 근거가 있는지 판정해 주세요. 어느 방법이 그린 엣지인지 모르는 상태로
판정해야 결과가 공정합니다.

## 2. 작업 폴더와 열어도 되는 것
이 세션은 작업 폴더 `/private/tmp/claude-502/-Users-igyulag-Develop-draftsman/f631bf55-255a-4657-8079-ccfb41a61fed/scratchpad/labelling-v3` 에서 엽니다. git 저장소가 아니어서 다른 맥락이 따라오지 않습니다.
열어도 되는 것은 이 폴더 안의 다음뿐입니다.

| 경로 | 용도 |
|---|---|
| `BRIEF.md` | 이 지시 |
| `RUBRIC.md` | 판정 기준 |
| `tasks.yaml` | 저장소 커밋과 프로덕션 범위 |
| `blind_edges.csv` | 입력이자 출력. `carried_from`이 빈 행만 고칩니다 |
| `repos/{spring-petclinic,jsoup,netty}` | 판정할 Java 소스. 읽기와 grep만 |

그 밖의 것은 열지도, 실행하지도 마세요. 특히 다음은 어느 방법이 무엇을 그렸는지 짐작하게
합니다.
- 작업 폴더 밖의 모든 것: 상위 디렉터리, 벤치마크를 만든 저장소와 그 문서, 결과, 이력
- `git log`, `git show`, `gh` 같은 이력과 이슈 조회(`repos/` 안의 Java 저장소 이력도 필요 없습니다)
- 어떤 다이어그램 도구나 그 출력. 판단은 소스 읽기와 grep으로만 합니다.

파일은 `blind_edges.csv` 하나만 고치세요.

## 3. 입력 (`blind_edges.csv`)
- `carried_from`이 채워진 행은 앞 라운드의 라벨입니다. 같은 유형을 판정할 때 참고만 하고 고치지
  마세요.
- 열:
  - `edge_id`: 엣지 번호(`V3-…`)
  - `repo`: 저장소
  - `focus`: T2는 포커스 클래스의 전체 이름, T1(저장소 전체 다이어그램)은 `-`
  - `source_name`, `target_name`: 다이어그램에 그려진 이름
  - `kind`: inheritance, association, dependency, nesting. `source`가 사용하거나, 상속하거나,
    포함하는 쪽입니다
  - `directed`: `false`이면 방향 없는 엣지(`--`, `..`)

## 4. 판정 기준
`RUBRIC.md`의 다음 절을 읽고 따르세요.
- "Names", "Top-level types"
- "Edge labels"의 판정 순서 1~5와 경계 사례 표, "Decided while writing the recall
  denominators" 표
- "Two levels, and nesting edges"
- "Decided at review": 익명 클래스를 이름 붙은 노드로 그린 경우 등 세 가지

테스트, 예제처럼 프로덕션 범위 밖 파일의 관계도 소스에 근거가 있으면 근거가 있는 것으로
봅니다.

## 5. 할 일
대상 행마다 아래 열을 채웁니다.

1. **`source_fqn`, `target_fqn`**: 그려진 이름을 소스의 실제 타입으로 해석합니다. 중첩
   타입이면 `Outer.Inner`까지 씁니다.
   - 같은 단순 이름이 여럿이면 포커스 클래스 파일의 import와 패키지로 가립니다(T1은 엣지
     반대쪽 타입의 import). 그래도 정해지지 않으면 후보를 `|`로 이어 적습니다.
   - 이름을 바꿔 그린 경우(약칭, 익명 클래스에 붙인 이름, `Outer_Inner` 표기)는 실제 타입으로
     해석하고 `note`에 `renamed`라고 적습니다. 익명 클래스는 감싸는 이름 있는 타입으로
     해석합니다.
   - JDK·프레임워크 타입은 `java.net.Socket`처럼 전체 이름을 씁니다.
   - 소스 어디에도 없는 이름이면 `?`를 씁니다.
2. **`label_drawn`, `file_line_drawn`**: 그려진 이름 그대로 판정합니다(중첩 타입은 별개의
   타입).
   - 판정 순서대로 처음 해당하는 하나: `unsupported` / `indirect` /
     `wrong_kind_or_direction` / `body_only` / `declared` / `undecidable`
   - 연관과 의존의 구분은 판정하지 않습니다.
   - nesting 엣지(`Outer +-- Inner`): Inner가 Outer 안에 선언돼 있으면 `declared`(그 선언 줄을
     인용), 방향이 뒤집혔으면 `wrong_kind_or_direction`, 그 밖에는 일반 엣지처럼 판정합니다.
3. **`label_top`, `file_line_top`**: 양 끝을 최상위 타입으로 접은 뒤 판정합니다. 대표 지표에
   쓰이는 칸입니다.
   - 근거도 접어서 찾습니다. 중첩 타입 안의 사용도 바깥 타입의 근거가 됩니다.
   - 양 끝이 같은 최상위 타입으로 접히면 `self`입니다(nesting 엣지는 모두).
   - 종류 판정도 접은 근거로 합니다. 상속으로 그린 엣지는 출발 쪽 안의 어떤 타입이 도착 쪽 안의
     어떤 타입을 상속하면 맞습니다. 상속이 아닌 종류는 두 최상위 타입이 직접 상속 관계이고 그
     밖에 아무 관계가 없을 때만 `wrong_kind_or_direction`입니다.
   - 같은 쌍에 근거가 여럿이면 가장 강한 근거(`declared` > `body_only`)를 고릅니다.
4. **인용 형식**: `저장소 기준 경로:줄`.
   - `unsupported`, `self`, `undecidable`이면 비워 둡니다.
   - 사용하는 쪽(출발 쪽) 최상위 타입의 파일에서, 상대 쪽 타입의 단순 이름이 있는 줄을
     고릅니다. `file_line_top`은 상대 쪽에 중첩된 타입의 이름이어도 됩니다.
5. **`unnamed`**: 근거가 타입 이름을 쓰지 않는 사용(그 타입의 필드에 대고 호출만 하는 경우
   등)이면 `true`, 아니면 `false`. 이런 엣지는 `unsupported`가 아니라 `body_only`입니다.
6. **`note`**: `renamed`, 판단이 애매했던 이유 등.

## 6. 보고
- 대상 88행의 두 수준별 라벨 건수와 `self`, `undecidable`, `?`, `renamed`, `unnamed` 건수
- 두 수준의 라벨이 다른 행(`edge_id`와 이유)
- 판단이 애매했던 행(`edge_id`와 이유). 사람 검수에서 먼저 봅니다.
- RUBRIC에서 모호했던 점
- 허용 목록 밖의 것을 열거나 실행하지 않았는지
