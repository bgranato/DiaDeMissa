"""One-shot: dedupe + enrich do catálogo de igrejas.

Roda diretamente contra o BD (sem passar pelo HTTP/auth). Usa a mesma lógica
de _eh_mesma_igreja e reverse_geocode da rota /admin/igrejas/limpar.
"""
from app.core.database import SessionLocal
from app.models.igreja import Igreja, UsuarioIgreja
from app.api.routes import _eh_mesma_igreja
from app.services.geocoding import reverse_geocode


def main():
    db = SessionLocal()
    try:
        todas = db.query(Igreja).all()
        print(f"Antes: {len(todas)} igrejas")

        grupos: list[list[Igreja]] = []
        for i in todas:
            achou = False
            for g in grupos:
                if _eh_mesma_igreja(g[0], i.nome, i.lat, i.lng):
                    g.append(i)
                    achou = True
                    break
            if not achou:
                grupos.append([i])

        duplicatas_removidas = 0
        for g in grupos:
            if len(g) > 1:
                def _peso(x):
                    tem_endereco = 1 if (x.endereco and x.endereco.strip()) else 0
                    # Prefere fonte Arquidiocese sobre OSM (oficial > comunitária)
                    fonte_oficial = 1 if (x.observacoes or "").startswith("Arquidiocese") else 0
                    return (-fonte_oficial, -tem_endereco, x.id)
                g_sorted = sorted(g, key=_peso)
                mestre = g_sorted[0]
                print(f"Grupo: {[(x.id, x.nome) for x in g_sorted]} → mestre id={mestre.id}")
                for outra in g_sorted[1:]:
                    favs = db.query(UsuarioIgreja).filter(UsuarioIgreja.igreja_id == outra.id).all()
                    for f in favs:
                        ja = db.query(UsuarioIgreja).filter(
                            UsuarioIgreja.usuario_id == f.usuario_id,
                            UsuarioIgreja.igreja_id == mestre.id,
                        ).first()
                        if ja:
                            db.delete(f)
                        else:
                            f.igreja_id = mestre.id
                    db.delete(outra)
                    duplicatas_removidas += 1
        db.commit()
        print(f"Duplicatas removidas: {duplicatas_removidas}")

        # Reverse geocode pra quem sobrou sem endereço
        sem_end = db.query(Igreja).filter(
            ((Igreja.endereco.is_(None)) | (Igreja.endereco == "")),
            Igreja.lat.isnot(None),
            Igreja.lng.isnot(None),
        ).all()
        print(f"Sem endereço: {len(sem_end)} (vai consultar Nominatim ~{len(sem_end)}s)")
        enriquecidos = 0
        for i in sem_end:
            rev = reverse_geocode(i.lat, i.lng)
            if rev and rev.get("endereco"):
                i.endereco = rev["endereco"]
                if not i.cidade and rev.get("cidade"):
                    i.cidade = rev["cidade"]
                if not i.estado and rev.get("estado"):
                    i.estado = rev["estado"]
                if not i.cep and rev.get("cep"):
                    i.cep = rev["cep"]
                enriquecidos += 1
                print(f"  id={i.id} {i.nome[:40]} → {i.endereco}")
        db.commit()
        print(f"Endereços enriquecidos: {enriquecidos}")
        print(f"Total final: {db.query(Igreja).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
