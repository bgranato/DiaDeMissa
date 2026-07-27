"""Lock de worker único do scheduler: com --workers 2, só um adquire o lock."""
from __future__ import annotations

from app.services import scheduler


def test_lock_exclusivo(tmp_path):
    lock = str(tmp_path / "sched.lock")
    fp1 = scheduler.tentar_lock_scheduler(lock)
    assert fp1 is not None, "primeiro worker deve adquirir o lock"
    # segundo 'worker' (outra descrição de arquivo) não consegue
    fp2 = scheduler.tentar_lock_scheduler(lock)
    assert fp2 is None, "segundo worker NÃO pode adquirir o lock"
    # ao liberar o primeiro, o próximo consegue
    fp1.close()
    fp3 = scheduler.tentar_lock_scheduler(lock)
    assert fp3 is not None, "após liberar, o lock fica disponível de novo"
    fp3.close()
