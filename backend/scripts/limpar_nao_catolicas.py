"""One-shot: limpa entradas claramente não-católicas do catálogo.

REGRAS DEFENSIVAS:
1. NUNCA toca em entradas da Arquidiocese (observacoes começa com 'Arquidiocese').
   Essas são oficialmente católicas por origem; qualquer match aqui é falso-positivo.
2. Padrões precisam ser FRASES INEQUÍVOCAS, não palavras soltas:
   - "Igreja Batista" (evangélica) ≠ "São João Batista" (santo católico).
3. Marker "espaço RD3", "kingdom hall", etc. — não são igrejas.
"""
from app.core.database import SessionLocal
from app.models.igreja import Igreja, UsuarioIgreja


# Padrões REGEX: precisam ser frases claras, não substrings perigosas.
import re

PADROES_NAO_CATOLICOS = [
    re.compile(r"\bigreja\s+batista\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+evang[eé]lica\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+pentecostal\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+presbiteriana\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+metodista\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+luterana\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+adventista\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+anglicana\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+messi[âa]nica\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+ortodoxa\b", re.IGNORECASE),
    re.compile(r"\bcat[óo]lica\s+apost[óo]lica\s+ortodoxa\b", re.IGNORECASE),
    re.compile(r"\bassembleia\s+de\s+deus\b", re.IGNORECASE),
    re.compile(r"\buniversal\s+do\s+reino\b", re.IGNORECASE),
    re.compile(r"\bkingdom\s+hall\b", re.IGNORECASE),
    re.compile(r"\btestemunhas?\s+de\s+jeová\b", re.IGNORECASE),
    re.compile(r"\bcentro\s+esp[íi]rita\b", re.IGNORECASE),
    re.compile(r"\b(igreja\s+)?renovada\s+em\s+cristo\b", re.IGNORECASE),
    re.compile(r"\bigreja\s+crist[ãa]\b\s*$", re.IGNORECASE),  # "Igreja Cristã" como nome completo
]

# Nomes claramente não-igreja
NAO_E_IGREJA = re.compile(r"^\s*(espaço|espaco)\s+\w", re.IGNORECASE)


def eh_nao_catolica(nome: str) -> bool:
    if not nome:
        return False
    if NAO_E_IGREJA.search(nome):
        return True
    return any(p.search(nome) for p in PADROES_NAO_CATOLICOS)


def main():
    db = SessionLocal()
    try:
        # 1) Audita: NUNCA toca em Arquidiocese, só nas demais
        candidatas = db.query(Igreja).filter(
            (Igreja.observacoes.is_(None)) | (~Igreja.observacoes.startswith("Arquidiocese"))
        ).all()
        print(f"Candidatas (não-Arquidiocese): {len(candidatas)}")

        a_deletar = []
        for i in candidatas:
            if eh_nao_catolica(i.nome or ""):
                a_deletar.append(i)
                print(f"  [DEL] id={i.id} {i.nome[:60]}")

        for i in a_deletar:
            db.query(UsuarioIgreja).filter(UsuarioIgreja.igreja_id == i.id).delete()
            db.delete(i)
        db.commit()

        print(f"\nDeletadas: {len(a_deletar)}")
        print(f"Total no BD: {db.query(Igreja).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
