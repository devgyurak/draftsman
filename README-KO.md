<!-- Korean translation of README.md. README.md is canonical; change both together. -->

<div align="center">

<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/draftsman-horizontal-reversed.svg">
    <img src="assets/logo/draftsman-horizontal.svg" alt="draftsman" width="380">
  </picture>
</h1>

**Claude Code와 Codex를 위한 UML 클래스 다이어그램 — 추측이 아니라 파서가 잰 사실로 그립니다**

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Languages](https://img.shields.io/badge/languages-Java%20%C2%B7%20C%23%20%C2%B7%20Kotlin%20%C2%B7%20TS%20%C2%B7%20Python%20%C2%B7%20C%2B%2B-D96A00)](#언어와-출력)
[![Agents: Claude Code · Codex](https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex-15181D)](#설치)

[동작 방식](#동작-방식) · [설치](#설치) · [쓰는 법](#쓰는-법) ·
[실제 프로젝트 검증](#실제-프로젝트-검증) · [하지 않는 것](#하지-않는-것) ·
[구성](#구성) · [English](README.md)

</div>

**제도사(draftsman)**는 측량된 수치를 받아, 숫자 하나 바꾸지 않고 도면으로 옮깁니다. Draftsman은 일을 그렇게
나누는 스킬입니다. 파서가 코드를 재고, 에이전트는 무엇을 보여줄지만 정하며, 렌더러가 그립니다.

- **파서가 잰 사실** — 클래스, 멤버, 상속, 다중성이 붙은 필드 연관, 시그니처와 어노테이션, (Java, C#, Kotlin, TypeScript, Python은) 메서드 본문에 적힌 타입 이름에서 나온 의존. 모두 소스 위치가 붙습니다.
- **편집할 뿐 지어내지 않음** — 에이전트는 숨기고, 묶고, 해설을 달 수 있습니다. 파서가 찾지 못한 관계는 근거를 단
  *추정* 엣지로만 넣을 수 있고, 점선으로 그려집니다.
- **어떤 크기에서도 읽히는 도면** — 한 클래스와 그 주변 *N*홉에 초점을 맞추고, getter·DTO·프레임워크 잡음은 패턴으로
  숨깁니다.
- **세 가지 출력** — 문서와 PR용 Mermaid, 정적 SVG, 그리고 검색·포커스/홉 조절·순환 강조·에이전트 해설이 들어간
  단일 파일 인터랙티브 HTML 뷰어.

<p align="center">
  <img src="docs/images/example-shop.svg" alt="예시: Java shop fixture를 SVG로 그린 결과" width="760">
</p>

## 동작 방식

```mermaid
flowchart LR
    S[소스 코드] --> E["extract.py<br/>tree-sitter"]
    E --> IR[("ir.json<br/>사실")]
    IR --> A["에이전트<br/>범위 판단"]
    A --> V[("view.json<br/>범위 · 숨김 · 그룹 · 해설")]
    IR --> R[render.py]
    V --> R
    R --> O["Mermaid · SVG · HTML"]
```

추출기는 코드에 적힌 것을 `ir.json`에 씁니다. 타입, 멤버, 관계, 그리고 해석하지 못한 이름입니다. 에이전트는
이 파일을 고치지 않고 다이어그램 텍스트를 직접 쓰지도 않습니다. 사실을 훑어본 뒤 `view.json`에 어느 클래스를
가운데 둘지, 몇 홉까지 볼지, 무엇을 숨기고 어떻게 묶을지, 무엇을 짚을지를 씁니다. `render.py`가 둘을 합치는데,
`ir.json`에 없는 관계는 뷰가 근거와 함께 추정으로 표시하지 않는 한 거부합니다.

보통은 명령 하나, `draw.py`가 모든 단계를 돌립니다. 추출하고, 범위를 정하고(타입이 30개쯤까지면 전부, 넘으면
포커스 클래스와 그 이웃), 렌더링하고, Mermaid를 검증합니다. 다이어그램과 함께 범위가 무엇을 담았는지, 한 홉 더
가면 무엇이 더해지는지, 무엇을 해석하지 못했는지를 보고하고, 에이전트는 그 보고로 고른 범위를 확인해 틀렸으면
다시 그린 뒤, 다이어그램과 범위와 미해결 참조를 함께 답합니다. 그룹, 해설, 강조는 같은 명령에 넘기는 뷰에 씁니다.

## 설치

이 저장소는 두 에이전트 모두를 위한 플러그인이자 마켓플레이스입니다.

**Claude Code**

```text
/plugin marketplace add devgyurak/draftsman
/plugin install draftsman@draftsman
```

**Codex** (CLI, IDE 확장, 앱이 플러그인 저장소를 함께 씁니다)

```bash
codex plugin marketplace add devgyurak/draftsman
codex plugin add draftsman@draftsman
```

Codex 안에서 `/plugins`를 실행해 *Draftsman*을 골라도 됩니다.

**스킬만**, 플러그인 없이 쓸 때:

| 에이전트 | 설치 |
|---|---|
| Codex | `$skill-installer install https://github.com/devgyurak/draftsman/tree/main/skills/draftsman` |
| Claude Code와 Agent Skills 형식을 읽는 다른 에이전트 | `skills/draftsman/`을 그 에이전트의 스킬 디렉터리에 그대로 복사 |

**필요한 것** — Python 3.10 이상과 패키지 세 개. 없으면 스킬이 처음 쓸 때 설치합니다.

```bash
pip install "tree-sitter>=0.25" tree-sitter-language-pack pyyaml
```

SVG 출력과 Mermaid 문법 검사에는 Node.js도 필요합니다:
`npm ci --prefix skills/draftsman/scripts`(elkjs, mermaid, jsdom을 `package-lock.json`에 고정된 버전으로
설치). HTML 출력은 없어도 되고, 그때 뷰어는 같은 버전의 elkjs를 CDN에서 불러옵니다.

## 쓰는 법

평소 말로 요청하면 됩니다. 클래스 다이어그램, 구조, 클래스 사이의 상속이나 의존을 묻는 요청에 스킬이 반응합니다.

> *"이 저장소 클래스 다이어그램 그려줘"*
> *"OrderService 주변 클래스를 인터랙티브로 보여줘"*
> *"Draw a class diagram of this repo."*

직접 부를 수도 있습니다.

```text
/draftsman [클래스이름 | 경로] [mermaid|svg|html] [members|public|no-members]   # Claude Code
/draftsman:draftsman OrderService html   # 같은 명령의 전체 이름(다른 /draftsman이 있을 때 필요)
$draftsman:draftsman                # Codex(플러그인). 스킬만 설치했다면 $draftsman
```

출력은 따로 말하지 않으면 용도에 따라 고릅니다. 문서·PR·대화 답변에는 Mermaid, 둘러보고 싶을 때나 클래스가 50개쯤을
넘으면 HTML 뷰어, 문서에 넣을 이미지나 슬라이드에는 SVG입니다. 위 다이어그램은
[`tests/fixtures/java/shop`](tests/fixtures/java/shop)을
[`docs/images/example-shop.view.json`](docs/images/example-shop.view.json)으로 그린 것입니다.

### 뷰

뷰는 고르고 주석을 달 뿐이며, 모든 키가 선택 사항입니다([모든 키](skills/draftsman/references/view-schema.md)).

```json
{
  "focus": "OrderService",
  "hops": 2,
  "hidden": ["*#get*", "*#set*", "*#toString"],
  "notes": [{"target": "Order", "text": "Customer와 양방향"}]
}
```

멤버 표시는 클래스마다 다르게 줄 수 있습니다. `"members": {"*": "none", "OrderService": "all"}`는
포커스 클래스만 멤버까지 그리고 주변은 이름만 그립니다. `--members all|public|none`은 한 번의 렌더에서
뷰 설정을 덮어씁니다.

### 스크립트만 쓰기

```bash
cd skills/draftsman
python3 scripts/draw.py path/to/src --focus Order --hops 1   # 아래 단계를 한 번에
python3 scripts/draw.py /tmp/draftsman-…/ir.json --view view.json --format svg -o d.svg
python3 scripts/extract.py path/to/src -o ir.json --exclude '**/test/**'   # *.gradle.kts는 건너뜀
python3 scripts/summary.py ir.json                  # 규모, 허브 클래스, 미해결 참조
python3 scripts/summary.py ir.json --type Order     # 타입 하나 자세히
python3 scripts/render.py ir.json view.json -o diagram.mmd     # 또는 --format svg | html
python3 scripts/render.py ir.json view.json --format svg --members none -o bare.svg
scripts/validate.sh diagram.mmd
```

## 언어와 출력

| 지금 되는 것 | 아직 안 되는 것 |
|---|---|
| Java, C#, Kotlin, TypeScript/TSX, Python, C++ 추출 | diff 모드(두 커밋 사이에 바뀐 클래스) |
| Mermaid(문법 검증), 정적 SVG(ELK 배치), 인터랙티브 HTML | PlantUML 출력, Graphviz 배치 |
| 포커스 + 홉, 숨김 패턴, 그룹, 해설, 하이라이트, 추정 엣지, 순환 | MCP 서버, LSP 기반 정밀 모드 |
| `/draftsman`이 있는 Claude Code 플러그인, `$draftsman:draftsman`이 있는 Codex 플러그인 | Go와 Rust(암묵적 인터페이스, 흩어진 `impl` 블록: 설계상 범위 밖) |

언어별로 알려진 한계는 [`lang-notes.md`](skills/draftsman/references/lang-notes.md)에 있습니다.

## 실제 프로젝트 검증

언어마다 실제 프로젝트에서 끝까지 돌려 봤습니다. 추출한 뒤 포커스를 둔 Mermaid(문법 검증), SVG, HTML 뷰어를
만들었고, 테스트와 생성 코드는 제외했습니다.

| 언어 | 프로젝트 | 파일 | 타입 | 관계 | 미해결 | 파싱 진단 |
|---|---|---:|---:|---:|---:|---:|
| Java | [spring-petclinic](docs/e2e/java/spring-petclinic.md) | 30 | 25 | 74 + 27 body | 0 | 0 |
| Java | [jsoup](docs/e2e/java/jsoup.md) | 105 | 230 | 1310 + 1724 body | 0 | 0 |
| Java | [Netty](docs/e2e/java/netty.md) | 2076 | 2752 | 17812 + 13818 body | 3 (2 outside, 1 unexplained) | 0 |
| C# | [eShopOnWeb](docs/e2e/csharp/eshoponweb.md) `src/` | 209 | 208 | 366 + 206 body | 194 (1 ambiguous, 193 outside) | 0 |
| C# | [eShop](docs/e2e/csharp/eshop.md) `src/` | 497 | 506 | 960 + 442 body | 513 (1 ambiguous, 508 outside, 4 unexplained) | 0 |
| C# | [Serilog](docs/e2e/csharp/serilog.md) `src/Serilog` | 113 | 119 | 566 + 363 body | 23 (23 outside) | 0 |
| Kotlin | [nowinandroid](docs/e2e/kotlin/nowinandroid.md) | 226 | 237 | 416 + 107 body | 4 (3 outside, 1 unexplained) | 0 |
| Kotlin | [Ktor](docs/e2e/kotlin/ktor.md) | 1578 | 2137 | 6897 + 2872 body | 586 (49 ambiguous, 537 outside) | 0 |
| TypeScript | [nest](docs/e2e/typescript/nest.md) `packages/` | 730 | 738 | 2307 + 1117 body | 0 | 0 |
| TypeScript | [TypeORM](docs/e2e/typescript/typeorm.md) `packages/typeorm/src` | 496 | 694 | 3968 + 2076 body | 1 (1 unexplained) | 0 |
| Python | [httpx](docs/e2e/python/httpx.md) | 23 | 87 | 283 + 152 body | 0 | 0 |
| Python | [Django](docs/e2e/python/django.md) `django/` | 879 | 1964 | 1865 + 3203 body | 0 | 0 |
| C++ | [leveldb](docs/e2e/cpp/leveldb.md) | 102 | 161 | 885 | 2 (2 unexplained) | 8개 파일에 9구간 (5구간은 함수 본문; `extern "C"`, `__has_include`, gMock 매크로, 멤버 함수 포인터 필드 하나) |
| C++ | [POCO](docs/e2e/cpp/poco.md) | 2317 | 2066 | 9983 | 309 (1 ambiguous, 4 outside, 304 unexplained; 시스템·라이브러리 헤더, POCO의 `#define` 타입) | 121개 파일에 333구간 (`#if` 분기, 멤버 포인터, 명시적 인스턴스화, `typeid`) |

Java, C#, Kotlin, TypeScript, Python의 관계 수는 선언에서 나온 관계와, 그 뒤에 메서드 본문에 적힌 이름(`new Foo()`,
`Foo.bar()`)에서 나온 관계입니다. Java, C#, Kotlin, TypeScript의 열 프로젝트에서 본문 관계는 모든 자리가 컴파일러의
해석과 일치합니다. Java는 javac와 대조했고(`bench/javac_oracle`. jsoup은 벤치마크가 빼는 `org.jsoup.examples`의 22개를
제외), C#은 Roslyn과 대조했습니다(`bench/roslyn_oracle`. 저장소가 고정한 SDK를 담은 컨테이너에서, 한 파일의 모든
컴파일(대상 프레임워크·프로젝트마다)이 같은 답을 내야 합니다. eShop의 MAUI 앱은 일반 `net11.0`으로 컴파일하고 플랫폼
코드는 제외). Kotlin은 Kotlin 컴파일러와 대조했습니다(`bench/kotlin_oracle`. 저장소 자신의 Gradle 빌드에 넣은
컴파일러 플러그인으로, 컨테이너에서. 한 파일의 모든 컴파일(타깃마다)이 같은 답을 내야 하고, Linux에서 빌드할 수 없는
애플 타깃은 제외). TypeScript는 TypeScript 컴파일러와 대조했습니다(`bench/tsc_oracle`). Python에는 컴파일러가 없어 mypy,
pyright, ty 셋이 같은 선언을 가리키는 자리를 답으로 삼습니다(`bench/py_oracle`. 스스로 도달 불가로 표시한 자리에서
정의를 내놓지 않은 검사기는 기권하고, 나머지가 정합니다). httpx와 Django(4065개)에서 그린 이름이 모두 일치합니다.

미해결 참조는 이유별로 나눴습니다. *ambiguous*는 같은 이름의 프로젝트 타입이 있어 후보로만 적고 고르지 않은 것,
*outside*는 소스 밖에 있는 것(와일드카드·기본 import, 외부 상위 타입의 중첩 타입)으로만 설명되는 것,
*unexplained*는 둘 다 아닌 것입니다. 프로젝트마다 [`docs/e2e/`](docs/e2e/README.md) 아래에 고정한 커밋, 실행
명령, 미해결 이름과 진단 하나하나의 원인을 적은 문서가 있습니다.

## 하지 않는 것

- **관계를 추측하지 않습니다.** `ir.json`에 없는 것은 거부합니다. 예외는 알려진 이름이나 미해결 이름 사이의 추정
  엣지뿐이고, 그것도 점선으로 그립니다.
- **메서드 본문은 타입 이름만, Java, C#, Kotlin, TypeScript, Python에서만 읽습니다.** `new Foo()`, `Foo.bar()`, 캐스트, 지역 변수 타입은 본문에서
  읽은 의존으로 표시됩니다. 값에 대한 호출이 닿는 곳(`order.total()`)은 읽지 않고, 다른 언어의 본문은 아직 읽지
  않습니다([#5](https://github.com/devgyurak/draftsman/issues/5)). 호출 그래프나 시퀀스 다이어그램 도구가 아닙니다.
- **컴포지션과 집합을 구분하지 않습니다** — 문법으로는 알 수 없습니다. 예외는 C++ 소유권입니다(값과
  `unique_ptr` 대 포인터·참조·`shared_ptr`).
- **코드를 실행하거나 밖으로 보내지 않습니다.** 모든 작업은 로컬에서 돌고, 네트워크는 위 의존성을 설치할 때(그리고
  HTML 뷰어의 CDN 대체 경로)만 씁니다.

## 구성

```text
skills/draftsman/
├── SKILL.md            작업 흐름, 절대 규칙, 범위와 출력 고르는 법
├── agents/openai.yaml  Codex 표시 이름과 기본 프롬프트
├── queries/            언어마다 tree-sitter 쿼리 하나: 무엇을 잡을지
├── scripts/            draw.py · extract.py · summary.py · render.py · validate.sh · layout.mjs
│   └── draftsman/      라이브러리: 추출기, 이름 해석, 장면, 렌더러, langs/
├── assets/             draw.js(SVG와 뷰어가 함께 씀) · viewer.html
├── config/             wrappers.yaml: 꿰뚫어 볼 컨테이너 타입(List<T> → T, *)
└── references/         스키마와 언어 노트, 필요할 때만 읽음
.claude-plugin/         Claude Code 플러그인·마켓플레이스 매니페스트
.codex-plugin/ · .agents/   Codex 플러그인 매니페스트와 마켓플레이스
```

| 문서 | 내용 |
|---|---|
| [`SKILL.md`](skills/draftsman/SKILL.md) | 에이전트의 작업 흐름, 절대 규칙, 범위와 출력 고르는 법 |
| [`ir-schema.md`](skills/draftsman/references/ir-schema.md) | `ir.json`의 모든 필드와 관계마다 어디서 나오는지 |
| [`view-schema.md`](skills/draftsman/references/view-schema.md) | `view.json`의 모든 키, 세 가지 출력, 예시 |
| [`setup.md`](skills/draftsman/references/setup.md) | 의존성: pip, uv 대안, 샌드박스, SVG와 Mermaid 검사용 Node |
| [`lang-notes.md`](skills/draftsman/references/lang-notes.md) | 언어별 동작과 알려진 한계 |
| [`query-protocol.md`](skills/draftsman/references/query-protocol.md) | 언어 쿼리가 쓰는 캡처 이름, 언어 추가하기 |
| [`docs/DESIGN.md`](docs/DESIGN.md) | 설계 노트: 배경, 원칙, 아키텍처, 로드맵 |
| [`docs/e2e/`](docs/e2e/README.md) | 측정한 프로젝트마다 한 페이지: 고정 커밋, 실행 명령, 결과, 미해결 이름과 진단의 원인 |
| [`CHANGELOG.md`](CHANGELOG.md) | 기존 `ir.json`/`view.json`에 영향을 주는 변경 |
| [`assets/logo/GUIDELINES.md`](assets/logo/GUIDELINES.md) | 로고 파일, 색, 여백, 최소 크기 |

## 개발과 기여

**준비물** — [uv](https://docs.astral.sh/uv/). SVG와 Mermaid 테스트에는 Node.js.

```bash
uv sync                                         # Python 의존성
npm ci --prefix skills/draftsman/scripts   # 선택: ELK 배치 + Mermaid 검사
uv run pytest                                   # draw.js와 뷰어의 node 테스트 포함.
                                                # Node가 없으면 건너뜀
```

테스트는 `tests/`에 있고, 여섯 언어 모두 같은 `shop` fixture를 씁니다. 언어 하나는 tree-sitter 쿼리와 작은
스펙 하나입니다. [캡처 규약](skills/draftsman/references/query-protocol.md)대로 `queries/<lang>.scm`을 쓰고,
`scripts/draftsman/langs/`에 `LanguageSpec`을 더하고, `tests/fixtures/<lang>/`에 같은 `shop` fixture를 만듭니다.

이슈와 PR을 환영합니다. 실제 프로젝트에서 나온 버그 리포트라면 더 좋습니다.
[`CONTRIBUTING.md`](CONTRIBUTING.md)(영문)에 관계를 지어내지 않는다는 원칙, 변경할 위치, 수정을 테스트하는 방법,
[엔드투엔드 프로젝트](docs/e2e/README.md)를 다시 돌려야 하는 경우가 정리되어 있습니다.

## 라이선스

[Apache License 2.0](LICENSE). 외부 구성 요소는 함께 배포하지 않고 사용자가 설치합니다.
[`NOTICE`](NOTICE)를 보세요.
