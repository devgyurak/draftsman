# Draftsman 설계 노트

> 프로젝트명: **Draftsman**
> 상태: 구상 단계 (2026-11-16)
> 한 줄 요약: **LLM이 관계를 지어내지 않는 클래스 다이어그램 스킬**

**이름의 의미**: Draftsman은 측량된 수치를 받아 도면을 그리는 제도사를 뜻한다. 이 프로젝트의 역할 분담과 같다. 측량(사실 수집)은 tree-sitter 파서가 하고, 제도사(Claude)는 그 수치를 바꾸지 않은 채 무엇을 어떻게 보여줄지만 정한다.

---

## 1. 배경

- Understand Anything은 코드베이스를 **지식 그래프**로 만드는 도구라서, UML 클래스 다이어그램과는 목적이 다르다.
- JVM 전용 도구(code-atlas, uml-reverse-mapper)는 바이트코드 기반이라 다른 언어로 확장할 수 없다.
- 이미 나와 있는 Claude 스킬은 대부분 **Claude가 코드를 직접 읽고 다이어그램을 쓰는 방식**이다.
  - 가장 가까운 것은 `athola/claude-night-market`의 `class-diagram`이다. explorer 에이전트가 구조 모델을 만들고 Mermaid로 변환하지만, 구조 모델을 만드는 주체가 LLM이다.
  - 나머지(`uml-modeling`, `diagram-generator`, `plantuml` 계열)는 grep으로 훑거나 사용자의 설명을 UML 문법으로 옮겨주는 수준이다.
- 파서 기반 도구(`tree-sitter-analyzer`의 `--uml class`)는 추출까지만 하고, 범위를 정하는 판단 레이어가 없다.

**비어 있는 자리**: tree-sitter로 결정적으로 추출하고, Claude는 범위와 표현만 판단하는 조합.

---

## 2. 핵심 원칙

### 파서는 사실, Claude는 편집

| 역할 | 담당 | 하는 일 |
|---|---|---|
| 사실 수집 | tree-sitter 파서 | 타입, 멤버, 상속/구현, 필드 타입 참조 추출 |
| 편집 판단 | Claude | 범위, 노이즈 제거, 그룹핑, 멤버 선별, 해설, 출력 형식 선택 |
| 배치 | 레이아웃 엔진 | 노드 좌표와 엣지 라우팅 (Claude가 좌표를 직접 그리지 않음) |

### 금지 규칙

- `ir.json`에 없는 관계를 사실처럼 그리지 않는다.
- 예외: 파서가 해석하지 못한 타입은 Claude가 추정할 수 있다. 단, 반드시 **점선이나 `<<inferred>>` 표시**로 사실과 구분한다.
- composition과 aggregation은 문법만으로 구분할 수 없으므로 기본 IR에서 제외한다. C++만 예외로 한다(4장 참고).

---

## 3. 1차 대상 언어

**Java, C#, Kotlin, TypeScript, Python, C++**

- 엄밀히 OOP를 강제하는 언어는 Java와 C# 정도다. 하지만 여섯 언어 모두 실무 코드가 클래스 중심이고, 상속을 명시적으로 쓰는 nominal 타이핑이 기본이다.
- 암묵적 인터페이스를 쓰는 언어(Go)와 impl 블록이 흩어지는 언어(Rust)는 제외한다. 이 덕분에 IR이 단순해진다.

### 언어별 난이도와 함정

| 언어 | 난이도 | 주요 함정 |
|---|---|---|
| Java | 쉬움 | record, sealed, 내부 클래스, 본문이 있는 enum |
| C# | 쉬움~중간 | `partial class` 파일 간 병합, property, record/struct, extension method는 멤버가 아님 |
| Kotlin | 중간 | 주 생성자 프로퍼티(`class A(val x: Int)`)를 필드로 처리, object/companion, `by` 위임, extension function, **tree-sitter grammar 완성도 사전 검증 필요** |
| TypeScript | 중간 | 파라미터 프로퍼티(`constructor(private x: X)`), `type` 별칭 포함 여부, declaration merging, 명시적 implements만 신뢰 |
| Python | 중간~어려움 | 필드는 `__init__`의 `self.x =`, dataclass 어노테이션, 클래스 변수에서 수집. 타입 힌트가 없으면 association 불가. Protocol/ABC, 다중 상속 |
| C++ | 어려움 | .h/.cpp 병합(정규화된 이름 기준), 매크로로 인한 파싱 실패, 템플릿, public/private 상속, struct/class 기본 접근 제한자 차이 |

### 진행 순서

1. **Java → C# → Kotlin**: 구조가 비슷해서 IR과 렌더러를 굳히기 좋다. C#의 partial 병합 로직은 나중에 C++ 헤더/소스 병합에 재사용한다.
2. **TypeScript → Python**: 타입 정보가 선택적인 언어들. 타입을 모를 때의 정책(생략할지, 점선으로 그릴지)을 이 단계에서 정한다.
3. **C++**: 파싱 실패를 우아하게 처리하는 구조가 갖춰진 뒤에 진행한다.

---

## 4. 아키텍처

```
소스 코드
   │
   ▼
[언어별 extractor]  tree-sitter + queries/<lang>.scm
   │
   ▼
ir.json      ← 사실 (파서 산출물, Claude가 수정하지 않음)
   │
   ├──── Claude 판단 ────▶ view.json  ← 편집 결정
   │                          │
   ▼                          ▼
[renderer]  ir.json + view.json 병합
   │
   ├─▶ Mermaid / PlantUML
   ├─▶ 정적 SVG (Graphviz dot 또는 ELK 배치)
   └─▶ 인터랙티브 HTML (뷰어 템플릿 + JSON 주입)
```

### 4.1 ir.json (사실)

```
Type {
  id, name, qualified_name,
  kind: class | interface | abstract_class | enum | record | struct | object | trait | mixin,
  modifiers[], generics[], members[], location { file, line }, language
}

Member {
  name, kind: field | method | property | constructor,
  visibility, type_ref, static, abstract
}

Relation {
  from, to,
  kind: extends | implements | association | dependency,
  multiplicity?: "1" | "0..1" | "*",
  ownership?: owned | shared | unknown,   // C++ 전용
  source_location
}

Unresolved {
  from, raw_type, location        // 파서가 해석하지 못한 타입 참조
}
```

- `ownership`은 C++에만 채운다. 값 멤버나 `unique_ptr<T>`는 `owned`(composition), 포인터나 `shared_ptr`는 `shared`(association)로 본다.
- `Unresolved`는 Claude가 추정할 수 있는 후보 목록이다.

### 4.2 view.json (Claude의 편집 결정)

```
{
  focus: "OrderService" | null,
  hops: 2,
  hidden: [type_id | member_pattern],
  groups: [{ name: "결제 도메인", members: [type_id] }],
  highlights: [{ target, reason }],          // 예: 순환 참조, 갓 클래스
  notes: [{ target, text }],                 // Claude의 해설
  inferred_edges: [{ from, to, kind, rationale }],  // 반드시 점선/<<inferred>>로 렌더링
  output: "mermaid" | "svg" | "html"
}
```

사실과 편집을 파일로 분리했기 때문에 "이 선이 왜 있지?"를 바로 추적할 수 있다.

### 4.3 타입 래퍼 풀기 (`config/wrappers.yaml`)

| 원본 | 결과 |
|---|---|
| `List<T>`, `std::vector<T>`, `list[T]`, `T[]`, `Array<T>` | `T`, 다중성 `*` |
| `Optional<T>`, `T?`, `T \| None`, `T \| undefined` | `T`, 다중성 `0..1` |

사용자가 자기 프로젝트의 래퍼 타입을 설정 파일에 추가할 수 있게 한다.

---

## 5. Claude의 판단 영역

| 영역 | 내용 |
|---|---|
| 범위 | 포커스 클래스와 홉 수 결정. 30개 이하면 전체, 초과하면 포커스 모드 |
| 노이즈 | getter/setter, `toString/equals/hashCode`, DTO 패키지, 테스트 클래스, 프레임워크 보일러플레이트 |
| 그룹핑 | 패키지와 무관하게 의미 단위로 클러스터 구성 |
| 멤버 선별 | 다이어그램의 목적에 맞는 필드와 메서드만 표시 |
| 해설 | 순환 참조, 상속 깊이, 갓 클래스 등 설계 냄새 지적 |
| 추정 | `Unresolved` 타입을 import와 맥락으로 추정 (`inferred` 표시 필수) |
| 출력 선택 | 아래 6장 기준 |

---

## 6. 출력 UI

| 출력 | 용도 | 생성 방식 |
|---|---|---|
| Mermaid / PlantUML | README, PR, 문서 | 텍스트 출력 (기본값) |
| 정적 SVG | 문서에 고정, 슬라이드 | Graphviz `dot` 또는 ELK로 배치, 색상과 강조는 view.json에서 반영 |
| 인터랙티브 HTML | 탐색, 온보딩 | 고정 템플릿 `assets/viewer.html`에 JSON 주입, 단일 파일로 출력 |

### 출력 선택 기준

- "문서에 넣을 거야" → Mermaid
- "보여줘", "탐색하고 싶어" → HTML
- 클래스 50개 초과 → HTML 우선

### 인터랙티브 HTML 뷰어

- **스택**: Cytoscape.js 또는 React Flow, 레이아웃은 ELK layered
- **기능**
  - 클래스를 클릭하면 멤버 목록 펼침
  - 포커스 클래스와 홉 수를 슬라이더로 조절
  - 검색
  - `inferred` 관계 표시/숨김 토글
  - 순환 참조 하이라이트
  - Claude 해설(notes)을 사이드 패널에 표시 ← **Understand Anything과의 차별점**
- 템플릿은 스킬에 고정한다. Claude가 매번 HTML을 새로 작성하지 않는다(일관성과 토큰 절약).

---

## 7. 스킬 구조

```
draftsman/
├── SKILL.md                 # 워크플로와 판단 규칙
├── scripts/
│   ├── extract.py           # 소스 → ir.json
│   ├── render.py            # ir.json + view.json → mermaid/svg/html
│   └── validate.sh          # mermaid-cli 문법 검증
├── queries/
│   ├── java.scm  csharp.scm  kotlin.scm
│   └── typescript.scm  python.scm  cpp.scm
├── config/
│   └── wrappers.yaml
├── assets/
│   └── viewer.html          # 인터랙티브 뷰어 템플릿
└── references/
    └── lang-notes.md        # 언어별 함정 (해당 언어 섹션만 읽음)
```

### SKILL.md 워크플로 초안

```markdown
---
name: draftsman
description: Java, C#, Kotlin, TypeScript, Python, C++ 코드에서 UML 클래스
  다이어그램을 생성한다. "클래스 다이어그램", "구조 그려줘", "상속 관계 보여줘" 등.
---

1. 대상 경로와 언어를 확인한다.
2. `python scripts/extract.py <path> -o ir.json` 실행.
3. ir.json의 타입 수를 확인한다.
   - 30개 이하: 전체를 그린다.
   - 초과: 사용자가 언급한 클래스를 중심으로 focus, hops 2.
     언급이 없으면 연결도가 높은 상위 클래스를 제시하고 고르게 한다.
4. 판단 결과를 view.json에 기록한다 (hidden, groups, notes, inferred_edges, output).
5. `python scripts/render.py ir.json view.json --format <output>`
6. Mermaid라면 `scripts/validate.sh`로 검증. 실패하면 view를 조정해서 재시도.

규칙:
- ir.json에 없는 관계는 절대 사실로 그리지 않는다.
- 추정한 관계는 inferred_edges에만 넣고 rationale을 남긴다.
- 해석하지 못한 타입은 마지막에 목록으로 따로 알린다.
```

### 구현 언어

- **1차는 Python**: `tree-sitter`와 `tree-sitter-language-pack`만 pip로 설치하면 되고, Claude 실행 환경에 거의 항상 있다.
- **이후 Rust CLI로 코어 이전 검토**: 스킬, CLI, MCP 서버가 같은 코어를 공유하는 구조. 플랫폼별 바이너리 빌드가 필요해서 처음부터 가면 배포가 무거워진다.

### 배포

Claude Code 플러그인 마켓플레이스 형태로 GitHub에 공개한다. `/plugin marketplace add`와 `/plugin install`로 설치하고, `/draftsman OrderService` 같은 슬래시 커맨드를 함께 제공한다.

---

## 8. 차별점 정리

1. **결정적 추출**: 관계를 LLM이 지어내지 않는다.
2. **사실/편집 분리**: ir.json과 view.json으로 출처를 추적할 수 있다.
3. **포커스 모드**: 특정 클래스 기준 N홉. 큰 코드베이스에서도 읽을 수 있는 다이어그램.
4. **추정의 명시**: `inferred` 표시로 신뢰도를 시각적으로 구분.
5. **해설이 붙은 뷰어**: Claude가 짚은 설계 냄새가 다이어그램 위에 같이 표시된다.
6. **쿼리 파일만으로 언어 추가**: 커뮤니티 기여 장벽이 낮다.

향후 후보: diff 모드(두 커밋 사이의 변경 클래스와 관계 하이라이트, PR 리뷰용), MCP 서버 노출, LSP 기반 정확도 모드(`--precise`).

---

## 9. 다음 단계

- [ ] GitHub, PyPI, npm에서 `draftsman` 이름 사용 가능 여부 확인 (선점됐다면 `draftsman-uml` 등 대안 검토)
- [ ] ir.json, view.json 스키마 확정
- [ ] Kotlin tree-sitter grammar로 실제 프로젝트 파싱 테스트
- [ ] Java용 `java.scm`과 `extract.py` 프로토타입
- [ ] `render.py` Mermaid 출력 + 포커스 모드
- [ ] `viewer.html` 템플릿 (Cytoscape.js 또는 React Flow + ELK)
- [ ] SKILL.md 작성, 실제 프로젝트로 판단 규칙 튜닝

---

## 참고

- [Understand Anything](https://github.com/Egonex-AI/Understand-Anything)
- [athola/claude-night-market – class-diagram](https://skills.sh/athola/claude-night-market/class-diagram)
- [tree-sitter-analyzer](https://pypi.org/project/tree-sitter-analyzer/)
- [CodeFrame](https://github.com/dxworks/codeframe)
- [tree-sitter-language-pack](https://github.com/xberg-io/tree-sitter-language-pack)
- [code-atlas (Gradle)](https://plugins.gradle.org/plugin/io.github.euledge.code-atlas)
- [uml-reverse-mapper](https://github.com/useful-java/uml-reverse-mapper)
