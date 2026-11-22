; Added to typescript.scm for TSX (LanguageSpec.extra_queries): the nodes only its
; grammar has.

; ---------------------------------------------------------------- bodies
; `</Foo>` repeats the opening tag's name, which is the one read
(jsx_closing_element) @body.blind
