"""Testes unitários do script de Fechamento Diário."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from prompts.fechamento_diario import (
    FOCOS_VALIDOS,
    CapturaDia,
    CapturaMelhoria,
    AprendizadoOperacional,
    SinteseFechamento,
    _contar_por_categoria,
    _timestamp_agora,
    _checksum_arquivo,
    _validar_sintese,
    _criar_sessao_padrao,
    _parse_args,
    executar,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def captura_padrao() -> CapturaDia:
    """Retorna CapturaDia com valores padrão para testes."""
    return CapturaDia(
        timestamp="2026-02-20T17:00:00Z",
        foco="fechamento",
        data_pregao="2026-02-20",
    )


@pytest.fixture()
def melhoria_tecnica() -> CapturaMelhoria:
    """Retorna melhoria técnica de exemplo."""
    return CapturaMelhoria(
        id="TECH-001",
        titulo="Otimizar cálculo de macro score",
        descricao="Refatorar algoritmo para reduzir latência",
        categoria="tecnico",
        prioridade="alta",
        esforco="medio",
    )


@pytest.fixture()
def melhoria_funcional() -> CapturaMelhoria:
    """Retorna melhoria funcional de exemplo."""
    return CapturaMelhoria(
        id="FEAT-001",
        titulo="Adicionar filtro de volatilidade",
        descricao="Filtrar sinais em momentos de alta volatilidade",
        categoria="funcional",
        prioridade="media",
        esforco="medio",
        sync_com=["AGENTE_AUTONOMO_FEATURES.md"],
    )


@pytest.fixture()
def melhoria_governanca() -> CapturaMelhoria:
    """Retorna melhoria de governança de exemplo."""
    return CapturaMelhoria(
        id="GOV-001",
        titulo="Automatizar atualização de checksums",
        descricao="Criar pipeline CI/CD para checksums automáticos",
        categoria="governanca",
        prioridade="baixa",
        esforco="grande",
    )


@pytest.fixture()
def melhoria_ml() -> CapturaMelhoria:
    """Retorna melhoria de ML/RL de exemplo."""
    return CapturaMelhoria(
        id="ML-001",
        titulo="Capturar padrão de reversão RSI < 30",
        descricao="Registrar setup para aprendizagem por reforço",
        categoria="ml_rl",
        prioridade="alta",
        esforco="grande",
        tipo_aprendizado="reinforcement",
    )


@pytest.fixture()
def sintese_completa(
    captura_padrao: CapturaDia,
    melhoria_tecnica: CapturaMelhoria,
    melhoria_funcional: CapturaMelhoria,
) -> SinteseFechamento:
    """Retorna síntese completa de exemplo."""
    return SinteseFechamento(
        captura=captura_padrao,
        aprendizados=AprendizadoOperacional(),
        melhorias=[melhoria_tecnica, melhoria_funcional],
    )


# ---------------------------------------------------------------------------
# Testes das constantes e configurações
# ---------------------------------------------------------------------------


class TestConstantes:
    """Testes das constantes do módulo."""

    def test_focos_validos_contem_tres_opcoes(self) -> None:
        """Deve ter exatamente 3 focos válidos."""
        assert len(FOCOS_VALIDOS) == 3

    def test_focos_validos_conteudo(self) -> None:
        """Deve conter abertura, meio_dia e fechamento."""
        assert "abertura" in FOCOS_VALIDOS
        assert "meio_dia" in FOCOS_VALIDOS
        assert "fechamento" in FOCOS_VALIDOS


# ---------------------------------------------------------------------------
# Testes das estruturas de dados
# ---------------------------------------------------------------------------


class TestCapturaDia:
    """Testes da dataclass CapturaDia."""

    def test_criacao_minima(self) -> None:
        """Deve criar com campos obrigatórios."""
        captura = CapturaDia(
            timestamp="2026-02-20T08:00:00Z",
            foco="abertura",
            data_pregao="2026-02-20",
        )
        assert captura.foco == "abertura"
        assert captura.data_pregao == "2026-02-20"
        assert captura.simbolo == "WINFUT"

    def test_valores_padrao(self, captura_padrao: CapturaDia) -> None:
        """Valores padrão devem ser zero/vazio."""
        assert captura_padrao.analises_rodadas == 0
        assert captura_padrao.trades_executados == 0
        assert captura_padrao.resultado_dia_pts == 0.0
        assert captura_padrao.eventos_macro == []
        assert captura_padrao.eventos_locais == []


class TestCapturaMelhoria:
    """Testes da dataclass CapturaMelhoria."""

    def test_categorias_validas(self) -> None:
        """Deve aceitar as 4 categorias previstas."""
        categorias = ["tecnico", "funcional", "governanca", "ml_rl"]
        for cat in categorias:
            m = CapturaMelhoria(
                id="FEAT-001",
                titulo="Teste",
                descricao="Descrição de teste",
                categoria=cat,
                prioridade="media",
                esforco="medio",
            )
            assert m.categoria == cat

    def test_sync_com_padrao_vazio(self, melhoria_tecnica: CapturaMelhoria) -> None:
        """sync_com deve ser lista vazia por padrão."""
        assert melhoria_tecnica.sync_com == []

    def test_sync_com_funcional(self, melhoria_funcional: CapturaMelhoria) -> None:
        """sync_com deve conter documentos relacionados."""
        assert "AGENTE_AUTONOMO_FEATURES.md" in melhoria_funcional.sync_com


class TestSinteseFechamento:
    """Testes da dataclass SinteseFechamento."""

    def test_para_dict_campos_obrigatorios(
        self, sintese_completa: SinteseFechamento
    ) -> None:
        """para_dict deve retornar campos obrigatórios."""
        dados = sintese_completa.para_dict()
        assert "captura_dia" in dados
        assert "aprendizados" in dados
        assert "melhorias" in dados
        assert "resumo" in dados

    def test_para_dict_resumo_contagens(
        self, sintese_completa: SinteseFechamento
    ) -> None:
        """resumo deve ter contagem correta de melhorias."""
        dados = sintese_completa.para_dict()
        resumo = dados["resumo"]
        assert resumo["total_melhorias"] == 2
        assert resumo["por_categoria"]["tecnico"] == 1
        assert resumo["por_categoria"]["funcional"] == 1
        assert resumo["por_categoria"]["governanca"] == 0

    def test_para_dict_itens_criticos(
        self, sintese_completa: SinteseFechamento
    ) -> None:
        """Deve listar apenas itens com prioridade alta."""
        dados = sintese_completa.para_dict()
        criticos = dados["resumo"]["itens_criticos"]
        assert len(criticos) == 1
        assert criticos[0]["id"] == "TECH-001"

    def test_para_dict_sincronizacao_fechamento(
        self, sintese_completa: SinteseFechamento
    ) -> None:
        """sync_manifest_atualizado deve ser True no foco fechamento."""
        dados = sintese_completa.para_dict()
        sync = dados["resumo"]["sincronizacao"]
        assert sync["backlog_atualizado"] is True
        assert sync["sync_manifest_atualizado"] is True

    def test_para_dict_sincronizacao_abertura(self) -> None:
        """sync_manifest_atualizado deve ser False no foco abertura."""
        captura = CapturaDia(
            timestamp="2026-02-20T08:00:00Z",
            foco="abertura",
            data_pregao="2026-02-20",
        )
        sintese = SinteseFechamento(
            captura=captura,
            aprendizados=AprendizadoOperacional(),
            melhorias=[],
        )
        dados = sintese.para_dict()
        assert dados["resumo"]["sincronizacao"]["sync_manifest_atualizado"] is False


# ---------------------------------------------------------------------------
# Testes das funções auxiliares
# ---------------------------------------------------------------------------


class TestContagemPorCategoria:
    """Testes de _contar_por_categoria."""

    def test_lista_vazia(self) -> None:
        """Lista vazia deve retornar zeros."""
        contagem = _contar_por_categoria([])
        assert contagem == {
            "tecnico": 0,
            "funcional": 0,
            "governanca": 0,
            "ml_rl": 0,
        }

    def test_uma_de_cada(
        self,
        melhoria_tecnica: CapturaMelhoria,
        melhoria_funcional: CapturaMelhoria,
        melhoria_governanca: CapturaMelhoria,
        melhoria_ml: CapturaMelhoria,
    ) -> None:
        """Deve contar corretamente uma de cada categoria."""
        melhorias = [
            melhoria_tecnica,
            melhoria_funcional,
            melhoria_governanca,
            melhoria_ml,
        ]
        contagem = _contar_por_categoria(melhorias)
        assert contagem == {
            "tecnico": 1,
            "funcional": 1,
            "governanca": 1,
            "ml_rl": 1,
        }

    def test_multiplas_mesma_categoria(
        self,
        melhoria_tecnica: CapturaMelhoria,
        melhoria_funcional: CapturaMelhoria,
    ) -> None:
        """Deve acumular corretamente para a mesma categoria."""
        contagem = _contar_por_categoria(
            [melhoria_tecnica, melhoria_tecnica, melhoria_funcional]
        )
        assert contagem["tecnico"] == 2
        assert contagem["funcional"] == 1


class TestTimestamp:
    """Testes de _timestamp_agora."""

    def test_formato_iso8601(self) -> None:
        """Deve retornar timestamp no formato YYYY-MM-DDTHH:MM:SSZ."""
        ts = _timestamp_agora()
        assert len(ts) == 20
        assert ts.endswith("Z")
        assert ts[4] == "-"
        assert ts[7] == "-"
        assert ts[10] == "T"
        assert ts[13] == ":"
        assert ts[16] == ":"


class TestChecksum:
    """Testes de _checksum_arquivo."""

    def test_arquivo_inexistente(self, tmp_path: Path) -> None:
        """Arquivo inexistente deve retornar string de erro."""
        resultado = _checksum_arquivo(tmp_path / "inexistente.txt")
        assert resultado == "arquivo_nao_encontrado"

    def test_arquivo_existente(self, tmp_path: Path) -> None:
        """Arquivo existente deve retornar checksum de 12 caracteres."""
        arq = tmp_path / "teste.txt"
        arq.write_text("conteúdo de teste", encoding="utf-8")
        checksum = _checksum_arquivo(arq)
        assert len(checksum) == 12
        assert checksum.isalnum()

    def test_checksum_deterministico(self, tmp_path: Path) -> None:
        """Mesmo arquivo deve gerar mesmo checksum."""
        arq = tmp_path / "teste.txt"
        arq.write_text("conteúdo fixo", encoding="utf-8")
        cs1 = _checksum_arquivo(arq)
        cs2 = _checksum_arquivo(arq)
        assert cs1 == cs2

    def test_checksum_diferente_conteudo_diferente(self, tmp_path: Path) -> None:
        """Arquivos com conteúdo diferente devem ter checksums diferentes."""
        arq1 = tmp_path / "a.txt"
        arq2 = tmp_path / "b.txt"
        arq1.write_text("conteúdo A", encoding="utf-8")
        arq2.write_text("conteúdo B", encoding="utf-8")
        assert _checksum_arquivo(arq1) != _checksum_arquivo(arq2)


# ---------------------------------------------------------------------------
# Testes de validação de schema
# ---------------------------------------------------------------------------


class TestValidarSintese:
    """Testes de _validar_sintese."""

    def test_dados_validos_sem_schema(self) -> None:
        """Sem schema disponível, não deve retornar erros."""
        dados = {
            "captura_dia": {"timestamp": "2026-02-20T17:00:00Z"},
            "aprendizados": {},
            "melhorias": [],
            "resumo": {},
        }
        with patch(
            "prompts.fechamento_diario._carregar_json", return_value={}
        ):
            erros = _validar_sintese(dados)
        assert erros == []

    def test_campo_obrigatorio_ausente(self) -> None:
        """Campo obrigatório ausente deve gerar erro."""
        schema = {
            "required": ["captura_dia", "aprendizados", "melhorias", "resumo"]
        }
        dados = {"captura_dia": {}, "aprendizados": {}}
        with patch(
            "prompts.fechamento_diario._carregar_json", return_value=schema
        ):
            erros = _validar_sintese(dados)
        assert any("melhorias" in e for e in erros)
        assert any("resumo" in e for e in erros)

    def test_foco_invalido(self) -> None:
        """Foco inválido deve gerar erro de validação."""
        schema = {
            "required": [],
            "properties": {
                "foco": {
                    "enum": ["abertura", "meio_dia", "fechamento"]
                }
            },
        }
        dados = {
            "captura_dia": {"foco": "invalido"},
            "aprendizados": {},
            "melhorias": [],
            "resumo": {},
        }
        with patch(
            "prompts.fechamento_diario._carregar_json", return_value=schema
        ):
            erros = _validar_sintese(dados)
        assert any("invalido" in e for e in erros)


# ---------------------------------------------------------------------------
# Testes da criação de sessão padrão
# ---------------------------------------------------------------------------


class TestCriarSessaoPadrao:
    """Testes de _criar_sessao_padrao."""

    def test_foco_abertura(self) -> None:
        """Deve criar sessão com foco abertura."""
        sintese = _criar_sessao_padrao("abertura", "2026-02-20")
        assert sintese.captura.foco == "abertura"
        assert sintese.captura.data_pregao == "2026-02-20"

    def test_foco_fechamento(self) -> None:
        """Deve criar sessão com foco fechamento."""
        sintese = _criar_sessao_padrao("fechamento", "2026-02-20")
        assert sintese.captura.foco == "fechamento"

    def test_melhorias_vazias(self) -> None:
        """Sessão padrão deve ter melhorias vazias."""
        sintese = _criar_sessao_padrao("meio_dia", "2026-02-20")
        assert sintese.melhorias == []

    def test_simbolo_padrao(self) -> None:
        """Deve usar WINFUT como símbolo padrão."""
        sintese = _criar_sessao_padrao("abertura", "2026-02-20")
        assert sintese.captura.simbolo == "WINFUT"

    def test_simbolo_variavel_ambiente(self) -> None:
        """Deve usar variável de ambiente FECHAMENTO_SIMBOLO se definida."""
        with patch.dict("os.environ", {"FECHAMENTO_SIMBOLO": "WDO"}):
            sintese = _criar_sessao_padrao("abertura", "2026-02-20")
        assert sintese.captura.simbolo == "WDO"


# ---------------------------------------------------------------------------
# Testes do parser de argumentos
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Testes de _parse_args."""

    def test_foco_abertura(self) -> None:
        """Deve aceitar --foco abertura."""
        args = _parse_args(["--foco", "abertura"])
        assert args.foco == "abertura"

    def test_foco_meio_dia(self) -> None:
        """Deve aceitar --foco meio_dia."""
        args = _parse_args(["--foco", "meio_dia"])
        assert args.foco == "meio_dia"

    def test_foco_fechamento(self) -> None:
        """Deve aceitar --foco fechamento."""
        args = _parse_args(["--foco", "fechamento"])
        assert args.foco == "fechamento"

    def test_data_personalizada(self) -> None:
        """Deve aceitar --data com data específica."""
        args = _parse_args(["--foco", "fechamento", "--data", "2026-01-15"])
        assert args.data == "2026-01-15"

    def test_verbose_flag(self) -> None:
        """Deve ativar modo verbose com --verbose."""
        args = _parse_args(["--foco", "abertura", "--verbose"])
        assert args.verbose is True

    def test_foco_invalido_levanta_erro(self) -> None:
        """Foco inválido deve causar SystemExit."""
        with pytest.raises(SystemExit):
            _parse_args(["--foco", "invalido"])

    def test_foco_obrigatorio(self) -> None:
        """--foco é obrigatório; deve causar SystemExit se ausente."""
        with pytest.raises(SystemExit):
            _parse_args([])


# ---------------------------------------------------------------------------
# Testes de execução
# ---------------------------------------------------------------------------


class TestExecutar:
    """Testes da função executar."""

    def test_abertura_cria_arquivo(self, tmp_path: Path) -> None:
        """Deve criar arquivo de saída para foco abertura."""
        saida = tmp_path / "saida.json"
        codigo = executar(
            foco="abertura",
            data_pregao="2026-02-20",
            caminho_saida=saida,
        )
        assert codigo == 0
        assert saida.exists()

    def test_meio_dia_cria_arquivo(self, tmp_path: Path) -> None:
        """Deve criar arquivo de saída para foco meio_dia."""
        saida = tmp_path / "saida_meio.json"
        codigo = executar(
            foco="meio_dia",
            data_pregao="2026-02-20",
            caminho_saida=saida,
        )
        assert codigo == 0
        assert saida.exists()

    def test_fechamento_cria_arquivo(self, tmp_path: Path) -> None:
        """Deve criar arquivo de saída para foco fechamento."""
        saida = tmp_path / "saida_fechamento.json"
        codigo = executar(
            foco="fechamento",
            data_pregao="2026-02-20",
            caminho_saida=saida,
        )
        assert codigo == 0
        assert saida.exists()

    def test_saida_conteudo_json_valido(self, tmp_path: Path) -> None:
        """Arquivo de saída deve conter JSON/YAML válido."""
        saida = tmp_path / "saida.json"
        executar(
            foco="fechamento",
            data_pregao="2026-02-20",
            caminho_saida=saida,
        )
        conteudo = saida.read_text(encoding="utf-8")
        assert "captura_dia" in conteudo
        assert "aprendizados" in conteudo
        assert "melhorias" in conteudo

    def test_data_invalida_retorna_codigo_2(self, tmp_path: Path) -> None:
        """Data inválida deve retornar código 2."""
        saida = tmp_path / "saida.json"
        codigo = executar(
            foco="fechamento",
            data_pregao="data-errada",
            caminho_saida=saida,
        )
        assert codigo == 2

    def test_foco_invalido_retorna_codigo_2(self, tmp_path: Path) -> None:
        """Foco inválido deve retornar código 2."""
        saida = tmp_path / "saida.json"
        codigo = executar(
            foco="invalido",  # type: ignore[arg-type]
            data_pregao="2026-02-20",
            caminho_saida=saida,
        )
        assert codigo == 2

    def test_cria_diretorio_pai(self, tmp_path: Path) -> None:
        """Deve criar diretórios intermediários automaticamente."""
        saida = tmp_path / "sub" / "dir" / "saida.json"
        codigo = executar(
            foco="abertura",
            data_pregao="2026-02-20",
            caminho_saida=saida,
        )
        assert codigo == 0
        assert saida.exists()

    def test_verbose_nao_altera_codigo_retorno(self, tmp_path: Path) -> None:
        """Modo verbose não deve alterar o código de retorno."""
        saida = tmp_path / "saida.json"
        codigo = executar(
            foco="abertura",
            data_pregao="2026-02-20",
            caminho_saida=saida,
            verbose=True,
        )
        assert codigo == 0


# ---------------------------------------------------------------------------
# Testes do ponto de entrada main
# ---------------------------------------------------------------------------


class TestMain:
    """Testes da função main."""

    def test_main_com_args_validos(self, tmp_path: Path) -> None:
        """main deve retornar 0 com argumentos válidos."""
        saida = str(tmp_path / "saida.json")
        codigo = main(["--foco", "abertura", "--data", "2026-02-20", "--saida", saida])
        assert codigo == 0

    def test_main_foco_invalido_retorna_erro(self) -> None:
        """main deve retornar erro para foco inválido."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--foco", "invalido"])
        assert exc_info.value.code != 0
