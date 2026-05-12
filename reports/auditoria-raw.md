# Auditoria Raw — outputs crus

=== 1. git tag -l ===
mini-gate-7-ok
pos-debug-postura

=== 2. git log --oneline -20 ===
c01628f Fase B + Gate 7: parsers Ato Penitencial, Leitura, versiculos. UI atualizada.
81008f6 Postura: parser generico com busca em janela de 3 linhas
bb88ad6 Snapshot inicial — pipeline 44/54, tela /canto funcional

=== 3. diff do fixture (HEAD~1) ===
diff --git a/backend/tests/fixtures/amissa_ascensao_2026.expected.json b/backend/tests/fixtures/amissa_ascensao_2026.expected.json
index ea54752..ed0d1a7 100644
--- a/backend/tests/fixtures/amissa_ascensao_2026.expected.json
+++ b/backend/tests/fixtures/amissa_ascensao_2026.expected.json
@@ -79,8 +79,8 @@
         {"numero": 1, "texto": "No meu primeiro livro, ó Teófilo, já tratei de tudo o que Jesus fez e ensinou, desde o começo,"},
         {"numero": 2, "texto": "até ao dia em que foi levado para o céu, depois de ter dado instruções pelo Espírito Santo, aos apóstolos que tinha escolhido."}
       ],
-      "conclusao": "Palavra do Senhor.",
-      "resposta": "Graças a Deus."
+      "conclusao": "Senhor.",
+      "resposta": "T. Graças a Deus."
     }
   ]
 }

=== 4. Contagem de testes ===
tests/test_ascensao_2026.py::TestIdempotencia::test_processar_duas_vezes_produz_mesmo_resultado

52 tests collected in 0.08s

=== 5. Funcoes de postura ===
19:def extrair_postura(linhas_bloco: list[str], janela: int = 3) -> Optional[str]:
39:def remover_marcacao_postura(texto: str) -> str:

=== 6. Hardcodes de postura ===
230:            postura = extrair_postura(blocos_linhas) or "de_pe"
309:            blocos.append(Dialogo(ordem=ordem, titulo="Saudação", postura="de_pe",
316:        blocos.append(Canto(ordem=1, titulo="Canto de Entrada", postura="de_pe",

=== 7. Pipeline output real ===
--- canto ordem=1 titulo="Canto de Entrada" ---
  postura: de_pe
  refrao: ['O Senhor foi preparar', 'um lugar para nós no céu.']
  estrofes(4):
    [1] Ó varões galileus, que estais no céu a olhar? Aleluia! | O Jesus que subiu ao céu deve, depois voltar! Aleluia!
    [2] Entre cantos e hinos triunfais se eleva o Senhor! Aleluia! | Cante a terra e o mar também: Cristo é vencedor! Aleluia!
    [3] Glorioso, à direita do Pai, sentou-se Jesus! Aleluia! Que nos foi preparar no céu, reino de eterna luz! Aleluia!
    [4] Ó Jesus, nosso Rei e Senhor, que subis para o céu! Aleluia! | Não deixeis os cristãos a sós: dai-nos o dom de Deus! Aleluia!

--- dialogo ordem=2 titulo="Saudação" ---
  postura: de_pe
  turnos(4):
    P: Em nome do Pai e do Filho e do Espírito Santo.
    T: Amém.
    P: A graça e a paz daquele que é, que era e que vem, estejam convosco.
    T: Bendito seja Deus, que nos reuniu no amor de Cristo.

--- dialogo ordem=4 titulo="Ato Penitencial" ---
  postura: None
  turnos(10):
    P: Irmãos e irmãs, reconheçamos os nossos pecados, para celebrarmos digna
    rubrica: Momento de silêncio
    P: Senhor, que subindo ao céu vos tornastes Rei do universo e Senhor dos 
    T: Senhor, tende piedade de nós.
    P: Cristo, que na vossa ascensão levastes cativo o cativeiro, tende pieda
    T: Cristo, tende piedade de nós.
    P: Senhor, que voltando à casa do Pai abristes o céu para nós, tende pied
    T: Senhor, tende piedade de nós.
    P: Deus todo-poderoso tenha compaixão de nós, perdoe os nossos pecados e 
    T: Amém.

--- leitura ordem=5 titulo="Primeira Leitura" ---
  postura: sentado
  versiculos: 11
    1o: #1 "No meu primeiro livro, ó Teófilo, já tratei de tud..."
  ult: #11 "que lhes disseram: “Homens da Galileia, por que fi..."
  conclusao: Senhor.
  resposta: T. Graças a Deus.


=== 8. pytest total ===
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 90 passed, 5 warnings in 5.53s ========================
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
