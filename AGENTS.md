# Gauntlet Loop obrigatório

Use este protocolo em toda mudança não trivial de código, comportamento, dados ou deploy.

1. Declare antes de alterar: **objetivo**, **métrica verificável**, **referência concreta** e **limite de escopo/tentativas**.
2. Separe construtor e crítico: a revisão deve partir do resultado real e da referência, sem reutilizar o raciocínio da implementação.
3. Corrija apenas os defeitos apontados e repita no máximo três vezes.
4. Se não convergir, não publique como concluído: preserve a versão boa, registre a evidência e peça revisão humana.
5. Antes de deploy, registre a evidência adequada ao risco: testes, typecheck/build, revisão independente e verificação pública.

Para montagem de missas, o PDF oficial é a referência. O gate cobre exclusivamente conteúdo e hierarquia litúrgicos; projeto editorial, diagramação e paginação ficam fora do escopo. Consulte `docs/GAUNTLET_LOOP.md` para o contrato operacional completo.
