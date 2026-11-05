from pathlib import Path

from criterios import carregar_criterios


def test_carrega_yaml_do_projeto() -> None:
    cfg = carregar_criterios(Path("criterios.yaml"))
    assert "notebook" in cfg["itens"]["palavras"]
    assert cfg["docs"]["tipos_prioritarios"]["edital_id"] == 2
    assert "perfil_usuario" in cfg


def test_arquivo_ausente_usa_defaults(tmp_path: Path) -> None:
    cfg = carregar_criterios(tmp_path / "nao_existe.yaml")
    assert cfg["valor"]["max"] == 5_000_000
