# Dia de Missa

Aplicação web para acompanhar a liturgia católica a partir dos folhetos oficiais
arquivados da Arquidiocese.

## Estrutura ativa

- `web/`: interface Vite/React publicada em `https://diademissa.com.br`.
- `backend/`: API FastAPI, pipeline de montagem e persistência.
- `docs/GAUNTLET_LOOP.md`: contrato de fidelidade litúrgica para a montagem das missas.

## Desenvolvimento

Backend:

```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

Frontend:

```bash
npm --prefix web run build
```

O pipeline de montagem usa o PDF oficial como referência e só publica conteúdo
aprovado pelo Gauntlet Loop. Artefatos locais, PDFs de cache, relatórios e
credenciais não fazem parte do repositório nem do release.
