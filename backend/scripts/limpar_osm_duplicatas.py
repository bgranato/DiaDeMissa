"""One-shot: remove igrejas importadas do OSM/Overpass que têm equivalente oficial
da Arquidiocese a ≤100m. Mantém os favoritos remapeados pra entrada oficial.

Não toca em igrejas Arquidiocese↔Arquidiocese próximas (são igrejas históricas distintas).
"""
from app.core.database import SessionLocal
from app.models.igreja import Igreja, UsuarioIgreja
from app.api.routes import _calc_distancia_km


def main():
    db = SessionLocal()
    try:
        osm = db.query(Igreja).filter(
            Igreja.observacoes.like("Importada de OpenStreetMap%"),
            Igreja.lat.isnot(None),
            Igreja.lng.isnot(None),
        ).all()
        oficiais = db.query(Igreja).filter(
            Igreja.observacoes.like("Arquidiocese%"),
            Igreja.lat.isnot(None),
            Igreja.lng.isnot(None),
        ).all()
        print(f"OSM: {len(osm)} | Arquidiocese: {len(oficiais)}")

        removidas = 0
        favoritos_remapeados = 0
        for o in osm:
            # Acha a Arquidiocese mais próxima
            melhor = None
            menor_d = 9999
            for arq in oficiais:
                d = _calc_distancia_km(o.lat, o.lng, arq.lat, arq.lng)
                if d < menor_d:
                    menor_d = d
                    melhor = arq
            if melhor and menor_d <= 0.1:  # 100m
                # Remapeia favoritos
                favs = db.query(UsuarioIgreja).filter(UsuarioIgreja.igreja_id == o.id).all()
                for f in favs:
                    ja = db.query(UsuarioIgreja).filter(
                        UsuarioIgreja.usuario_id == f.usuario_id,
                        UsuarioIgreja.igreja_id == melhor.id,
                    ).first()
                    if ja:
                        db.delete(f)
                    else:
                        f.igreja_id = melhor.id
                    favoritos_remapeados += 1
                print(f"  [DEL] id={o.id} {o.nome[:50]:50s} → mantém id={melhor.id} {melhor.nome[:40]} ({menor_d*1000:.0f}m)")
                db.delete(o)
                removidas += 1
            else:
                print(f"  [KEEP] id={o.id} {o.nome[:50]} (mais próxima Arquidiocese: {menor_d:.2f} km)")
        db.commit()
        print(f"\nRemovidas: {removidas} | Favoritos remapeados: {favoritos_remapeados}")
        print(f"Total no BD: {db.query(Igreja).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
