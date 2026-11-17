# POCO — C++

The POCO C++ Libraries: about 30 libraries (Foundation, Net, NetSSL, Crypto, Data with its
ODBC, MySQL, PostgreSQL and SQLite connectors, XML, JSON, Util, MongoDB, Redis, ...) with
platform files for Windows, POSIX and others, and macros for exports, deprecation and
exception classes.

| | |
|---|---|
| Repository | [github.com/pocoproject/poco](https://github.com/pocoproject/poco) |
| Commit | `2ef5cec8a9` (2026-11-17) |
| Extracted | the whole repository without tests (`testsuite/`, `Data/DataTest`, `CppUnit/`), `samples/`, `fuzzing/`, `Benchmark/` and the bundled third-party code (`dependencies/`, `Data/SQLParser`) |

Measured on 2026-11-17 with Draftsman `c6746b9`.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/pocoproject/poco poco && git -C poco checkout 2ef5cec8a9
cd poco
python3 "$DRAFTSMAN"/extract.py . --lang cpp \
  --exclude '**/testsuite/**' --exclude '**/samples/**' --exclude '**/dependencies/**' \
  --exclude '**/fuzzing/**' --exclude 'CppUnit/**' --exclude 'Benchmark/**' \
  --exclude 'Data/SQLParser/**' --exclude 'Data/DataTest/**' -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`dependencies/` holds zlib, expat, PCRE2, SQLite, the 7-Zip SDK and others; `Data/SQLParser`
is a bundled SQL parser with its own license. Their types are referenced from POCO and stay
unresolved below.

`view.json`:

```json
{
  "focus": "Logger",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 2317 files, 2065 types, relations: association 1920, dependency 6984, extends 893, implements 181, 326 unresolved (1 ambiguous, 7 outside the sources, 318 unexplained), 346 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2317 | 2065 | 1920 | 6984 | 893 | 181 | 326 (1 ambiguous, 7 outside, 318 unexplained) | 346 |

Types by kind: 1374 classes, 274 structs, 74 abstract classes, 65 interfaces, 278 enums.

The Mermaid and SVG renders of the view draw 37 types and 83 relations (`Poco::Logger` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 2065 types and 5372 relations and opens on the same focus. No inferred edges.

## Unresolved

326 references to 168 names. C++ has no wildcard import that could explain a name outside
the sources, so most are unexplained; the groups below cover all of them.

Outside the sources (265):

- Platform APIs, from system headers: Windows (71: `HANDLE` 17, `DWORD` 14,
  `SecurityFunctionTableW`, `CredHandle`, `HKEY`, ...) and POSIX and other systems (53:
  `sockaddr` 9, `pthread_mutex_t`, `timeval`, `sem_t`, `epoll_event`, `pid_t`; VxWorks'
  `SEM_ID` and `MODULE_ID`, HP-UX's `shl_t`, Solaris' `fp_except`).
- Libraries the connectors and wrappers bind to: ODBC (36: `SQLINTEGER`, `SQLSMALLINT`,
  `SQLHDBC`, ...), OpenSSL (35: `EVP_PKEY` 9, `X509`, `SSL_CTX`, `BIO`), DNS-SD and Avahi
  (24), MySQL (17), PostgreSQL (7), expat (5), the 7-Zip SDK (5), zlib (3), PCRE2 (3),
  SQLite (2; one *may come from wildcard import Poco::Data::Keywords::\**), Apache's
  `request_rec`.
- Nested types of `std` bases (3, outside): `openmode` in subclasses of `std::ios`,
  `int_type` in a `std::streambuf`.

Type macros of POCO's own (27): `poco_socket_t` 12, `poco_socklen_t` 12,
`poco_fcntl_request_t`, `poco_ioctl_request_t`, `POCO_LPQUERY_SERVICE_CONFIG`, defined with
`#define` per platform; Draftsman reads no `#define`.

Declared by the project where the parser does not see them (13): the exception classes of
`POCO_DECLARE_EXCEPTION(API, Name, Base)` (`SAXException` 4, `Poco::Data::DataException`,
`Poco::RemotingNG::RemoteException`, `XMLException`, `CryptoException`, `ODBCException`).
Macros are blanked, not expanded, so these classes are not drawn; each reference names the
macros that mention it, the file named after it first: *mentioned by
POCO_DECLARE_EXCEPTION(...) at XML/include/Poco/XML/XMLException.h:28, ...; one of them may
declare it*.

Gaps of Draftsman (20):

- Names that depend on a template parameter or a library alias (6):
  `typename ActRec::Ptr` and `typename MapType::iterator` (members of template
  parameters), `NamespaceManager::NamespaceMap::const_iterator` 2 and
  `SerializerGenerator::VarGet::const_iterator` (`const_iterator` of a member alias of a
  `std` container; the hint says the class has no such nested type), and `TStrategy` in a
  struct inside the partial specialisation `AbstractEvent<void, TStrategy, ...>`, which is
  not read as a type.
- Expressions read as types (7): `std::aligned_storage<sizeof(T), alignof(T)>` in
  `MPSCQueue` gives `sizeof` and `alignof`; `poco_static_assert(offsetof(Header, code) ==
  0x01);` in the body of `ICMPv4PacketImpl` is read as a declaration and gives
  `poco_static_assert`, `code`, `checksum`, `id` and `seq`.
- `Placeholder` (6, 3 of them outside): `Poco::Placeholder` is a `union`, and named unions
  are no types; the hint lists `Poco::Util::Units::Units::Prefix::Placeholder`, a project
  type of the same name out of scope.
- `XMLStreamSerializer` (1): only forward-declared in `ValueTraits.h`; POCO does not define
  it.

1 ambiguous: `Parser::SQLParserResult` in `Poco::Data::Statement`, from the excluded
`Data/SQLParser`; the three project classes called `Parser` are listed as candidates and
none is picked.

## Parse diagnostics

346 syntax-error spans in 124 files (139 of them in 53 headers). Declarations inside a span
may be missing; the rest of the file is read. Every class declared in a header is
extracted; what is lost is members near a span. By cause:

- Conditional compilation (100): each `#if` is read with its first branch, so an
  `if (...) {` in one branch and its `else` in another (`IPAddress.cpp` 21, `DNS.cpp`), a
  `#if __has_include(...)` (`Platform.h`, `SocketDefs.h`), or an `#if` inside an expression
  (`NetSSL_Win/src/Context.cpp`) breaks the code around it.
- Pointers to members (62): `typedef void (C::*FeatureSetter)(...)` in
  `AbstractSessionImpl.h`, `(_receiverObject->*_receiverMethod)(...)` in `Delegate.h` and
  `PriorityDelegate.h`, `ActiveRunnable.h`.
- Explicit instantiations (46): `extern template class ODBC_API Error<SQLHENV,
  SQL_HANDLE_ENV>;`, `extern template class Struct<std::string>;`.
- `typeid(...)` in expressions (36): `type == typeid(bool)` in `AbstractBinder.cpp` and
  `VarHolder.h`.
- Windows calling conventions and casts (14): `typedef DWORD (WINAPI *Entry)(LPVOID);`,
  `(CONST BYTE*) value` in `WinRegistryKey.cpp`.
- 88 others, mostly one or two each: `sizeof(struct in6_addr)` in an enum initialiser,
  `new T*[n]`, `typename X::y(...)` calls, `.operator bool()` calls, a `throw` in a
  conditional expression, `operator ++ ();` statements, Apache's `AP_MODULE_DECLARE_DATA`,
  OpenSSL's `STACK_OF(...)`, a leading macro after `static`
  (`static POCO_TUPLE_TYPE_HANDLER_INLINE void tupleBind(...)`), `class P = C*` defaults in
  `ObjectPool.h`, `std::function<bool()> stop = {}` parameters in `SSHChannelStream.h`,
  platform constants (`IEEE$M_STATUS_INV` in `FPEnvironment_DEC.h`).

## What it covers

- Export macros in mixed case between `class` and the name: more than 1100 header lines
  start with `class Foundation_API Logger: public Channel` and the like (`Net_API`,
  `NetSSL_Win_API`, `DNSSD_Bonjour_API`); also before functions (`Net_API std::ostream&
  operator << (...)`).
- Statement macros without `;` (`POCO_CHECK_MINMAX_MACROS` before the namespace, 204
  `POCO_DECLARE_EXCEPTION(...)` in headers) and attribute macros (77
  `POCO_DEPRECATED("...")`, before a declaration, after it or on an enumerator;
  `POCO_NODISCARD_CTOR`), blanked so the classes around them parse.
- Inherited member aliases (`using CharacterMap = int[256];` in `TextEncoding`, used by its
  subclasses) and base class names in derived classes (`CodeGenerator::Properties`).
- Scale: 2065 types in nested namespaces (`Poco::Data::ODBC`, `Poco::Net::Impl`), 438
  nested types; of 1920 associations, 1493 are `owned` and 427 `shared`. 129 `extends` relations
  reach 13 external classes, 12 of them in `std` (`std::ios` 43, `std::istream` 37,
  `std::ostream` 32) and quill's `Sink`.
