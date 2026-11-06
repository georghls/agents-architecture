"""Coletor nativo de telemetria, spans e persistência local (SQLite/JSONL).

Implementa rastreamento agnóstico a frameworks (LangGraph, AutoGen 0.4 e MCP stdio),
registrando cada ciclo com um `run_id` único, latência detalhada de cada etapa,
consumo de tokens e estimativa financeira, conforme D-015 em docs/decisions.md.
"""

import contextvars
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Optional
import uuid

from src.config import RAIZ_PROJETO
from src.observabilidade.custos import calcular_custo_execucao

DIRETORIO_DADOS = RAIZ_PROJETO / "data"
CAMINHO_BANCO_PADRAO = DIRETORIO_DADOS / "telemetria.db"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# 1. GESTÃO E CRIAÇÃO DO BANCO DE DADOS SQLITE
# ----------------------------------------------------------------------

def obter_caminho_banco(caminho_customizado: Optional[Path | str] = None) -> Path:
    if caminho_customizado:
        p = Path(caminho_customizado)
    else:
        env_path = os.environ.get("DATABASE_TELEMETRIA_PATH")
        p = Path(env_path) if env_path else CAMINHO_BANCO_PADRAO

    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def inicializar_banco(caminho_banco: Optional[Path | str] = None) -> Path:
    """Cria as tabelas de telemetria e spans caso ainda não existam."""
    banco = obter_caminho_banco(caminho_banco)
    with sqlite3.connect(banco) as conn:
        cursor = conn.cursor()
        
        # Tabela principal com agregações da execução (uma linha por pergunta)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execucoes (
                run_id TEXT PRIMARY KEY,
                padrao_arquitetural TEXT NOT NULL,
                pergunta TEXT NOT NULL,
                papel_usuario TEXT NOT NULL,
                resposta_final TEXT,
                timestamp_inicio TEXT NOT NULL,
                timestamp_fim TEXT NOT NULL,
                latencia_total_ms REAL NOT NULL,
                chamadas_llm INTEGER NOT NULL DEFAULT 0,
                chamadas_mcp INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                custo_usd REAL NOT NULL DEFAULT 0.0,
                custo_brl REAL NOT NULL DEFAULT 0.0,
                sucesso INTEGER NOT NULL DEFAULT 1,
                erro TEXT,
                metadados TEXT
            )
        """)

        # Tabela detalhada de spans (árvore de chamadas de nós, agentes e MCP)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                nome_span TEXT NOT NULL,
                tipo TEXT NOT NULL,
                timestamp_inicio TEXT NOT NULL,
                timestamp_fim TEXT NOT NULL,
                duracao_ms REAL NOT NULL,
                detalhes TEXT,
                FOREIGN KEY (run_id) REFERENCES execucoes(run_id)
            )
        """)

        # Tabela de avaliações de qualidade semântica e conformidade (Evals / LLM-as-a-Judge)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS avaliacoes (
                avaliacao_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                fidelidade_score REAL NOT NULL,
                relevancia_score REAL NOT NULL,
                seguranca_rbac_score REAL NOT NULL,
                houve_alucinacao INTEGER NOT NULL,
                falha_seguranca INTEGER NOT NULL,
                fatos_inventados TEXT,
                justificativa TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES execucoes(run_id)
            )
        """)

        # Índices para consultas rápidas no Dashboard
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execucoes_padrao ON execucoes(padrao_arquitetural)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execucoes_timestamp ON execucoes(timestamp_inicio)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spans_run_id ON spans(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_avaliacoes_run_id ON avaliacoes(run_id)")
        
        conn.commit()

    return banco


# ----------------------------------------------------------------------
# 2. GERENCIAMENTO DE CONTEXTO E SPANS
# ----------------------------------------------------------------------

class SpanContexto:
    """Representa uma etapa intermediária da execução (nó de grafo, turno ou chamada MCP)."""

    def __init__(self, trace: "TraceContexto", nome: str, tipo: str = "operacao", detalhes: Optional[dict] = None):
        self.trace = trace
        self.nome = nome
        self.tipo = tipo
        self.detalhes = detalhes or {}
        self.span_id = f"span_{uuid.uuid4().hex[:12]}"
        self.timestamp_inicio: str = ""
        self.timestamp_fim: str = ""
        self.duracao_ms: float = 0.0
        self._t0: float = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        self.timestamp_inicio = _agora_iso()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        t1 = time.perf_counter()
        self.duracao_ms = round((t1 - self._t0) * 1000.0, 2)
        self.timestamp_fim = _agora_iso()

        if exc_type is not None:
            self.detalhes["erro"] = str(exc_val)
            self.detalhes["tipo_erro"] = exc_type.__name__

        self.trace.registrar_span(self)
        return False  # Propaga exceções normalmente


class TraceContexto:
    """Gerenciador principal do ciclo de vida de uma pergunta / run_id."""

    def __init__(
        self,
        padrao_arquitetural: str,
        pergunta: str,
        papel_usuario: str = "geral",
        run_id: Optional[str] = None,
        caminho_banco: Optional[Path | str] = None,
    ):
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        self.padrao_arquitetural = padrao_arquitetural
        self.pergunta = pergunta
        self.papel_usuario = papel_usuario
        self.caminho_banco = caminho_banco

        self.timestamp_inicio = ""
        self.timestamp_fim = ""
        self.latencia_total_ms: float = 0.0
        self.resposta_final: str = ""
        self.chamadas_llm: int = 0
        self.chamadas_mcp: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.total_tokens: int = 0
        self.sucesso: bool = True
        self.erro: Optional[str] = None
        self.metadados: dict[str, Any] = {}
        self.evidencias_mcp: list[str] = []

        self.spans: list[dict[str, Any]] = []
        self._t0: float = 0.0
        self._token_contextvar = None

    def __enter__(self):
        self._t0 = time.perf_counter()
        self.timestamp_inicio = _agora_iso()
        self._token_contextvar = _trace_ativo.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        t1 = time.perf_counter()
        self.latencia_total_ms = round((t1 - self._t0) * 1000.0, 2)
        self.timestamp_fim = _agora_iso()

        if exc_type is not None:
            self.sucesso = False
            self.erro = f"{exc_type.__name__}: {str(exc_val)}"

        # Restaura o contexto anterior
        if self._token_contextvar is not None:
            _trace_ativo.reset(self._token_contextvar)

        # Salva o trace concluído no banco SQLite
        self.persistir()
        return False

    def span(self, nome: str, tipo: str = "operacao", detalhes: Optional[dict] = None) -> SpanContexto:
        """Cria e abre um sub-span associado a este trace."""
        return SpanContexto(self, nome=nome, tipo=tipo, detalhes=detalhes)

    def registrar_span(self, span: SpanContexto):
        """Registra os dados de um sub-span concluído."""
        self.spans.append({
            "span_id": span.span_id,
            "run_id": self.run_id,
            "nome_span": span.nome,
            "tipo": span.tipo,
            "timestamp_inicio": span.timestamp_inicio,
            "timestamp_fim": span.timestamp_fim,
            "duracao_ms": span.duracao_ms,
            "detalhes": span.detalhes,
        })

    def registrar_tokens(self, input_tokens: int, output_tokens: int):
        """Acumula tokens consumidos por chamadas de modelo."""
        self.input_tokens += max(0, int(input_tokens))
        self.output_tokens += max(0, int(output_tokens))
        self.total_tokens = self.input_tokens + self.output_tokens

    def registrar_chamada_llm(self, quantidade: int = 1):
        self.chamadas_llm += quantidade

    def registrar_chamada_mcp(self, quantidade: int = 1):
        self.chamadas_mcp += quantidade

    def registrar_evidencia_mcp(self, evidencia: str):
        """Armazena o trecho/evidência retornado pelo servidor MCP para auditoria do Juiz LLM (D-024)."""
        if isinstance(evidencia, str) and evidencia.strip():
            self.evidencias_mcp.append(evidencia.strip())
            self.metadados["evidencias_mcp"] = list(self.evidencias_mcp)

    def obter_contexto_mcp(self) -> str:
        """Retorna todas as evidências coletadas no MCP concatenadas."""
        return "\n\n".join(self.evidencias_mcp)

    def definir_resposta(self, resposta: str):
        self.resposta_final = resposta

    def persistir(self):
        """Salva a execução e todos os seus spans no banco SQLite local."""
        banco = inicializar_banco(self.caminho_banco)

        # Calcula o custo financeiro (incluindo chamadas de embedding do MCP - D-024)
        estimativa = calcular_custo_execucao(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            chamadas_embedding=self.chamadas_mcp,
        )

        with sqlite3.connect(banco) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO execucoes (
                    run_id, padrao_arquitetural, pergunta, papel_usuario,
                    resposta_final, timestamp_inicio, timestamp_fim,
                    latencia_total_ms, chamadas_llm, chamadas_mcp,
                    input_tokens, output_tokens, total_tokens,
                    custo_usd, custo_brl, sucesso, erro, metadados
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.run_id,
                    self.padrao_arquitetural,
                    self.pergunta,
                    self.papel_usuario,
                    self.resposta_final,
                    self.timestamp_inicio,
                    self.timestamp_fim,
                    self.latencia_total_ms,
                    self.chamadas_llm,
                    self.chamadas_mcp,
                    self.input_tokens,
                    self.output_tokens,
                    self.total_tokens,
                    estimativa["custo_total_usd"],
                    estimativa["custo_total_brl"],
                    1 if self.sucesso else 0,
                    self.erro,
                    json.dumps(self.metadados, ensure_ascii=False),
                ),
            )

            for s in self.spans:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO spans (
                        span_id, run_id, nome_span, tipo,
                        timestamp_inicio, timestamp_fim, duracao_ms, detalhes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["span_id"],
                        s["run_id"],
                        s["nome_span"],
                        s["tipo"],
                        s["timestamp_inicio"],
                        s["timestamp_fim"],
                        s["duracao_ms"],
                        json.dumps(s["detalhes"], ensure_ascii=False),
                    ),
                )

            conn.commit()


# Variável de contexto assíncrono para propagar o trace ativo entre nós e MCP
_trace_ativo: contextvars.ContextVar[Optional[TraceContexto]] = contextvars.ContextVar(
    "trace_ativo", default=None
)


def obter_trace_atual() -> Optional[TraceContexto]:
    """Retorna o trace de telemetria ativo na execução corrente, se houver."""
    return _trace_ativo.get()


def iniciar_rastreamento(
    padrao: str,
    pergunta: str,
    papel: str = "geral",
    run_id: Optional[str] = None,
    caminho_banco: Optional[Path | str] = None,
) -> TraceContexto:
    """Cria e inicia o contexto de rastreamento de uma execução."""
    return TraceContexto(
        padrao_arquitetural=padrao,
        pergunta=pergunta,
        papel_usuario=papel,
        run_id=run_id,
        caminho_banco=caminho_banco,
    )


# ----------------------------------------------------------------------
# 3. CONSULTAS ANALÍTICAS PARA O DASHBOARD DE LLMOPS
# ----------------------------------------------------------------------

def listar_execucoes(limite: int = 100, caminho_banco: Optional[Path | str] = None) -> list[dict[str, Any]]:
    """Retorna a lista das execuções mais recentes para a visualização no Dashboard."""
    banco = obter_caminho_banco(caminho_banco)
    if not banco.exists():
        return []

    with sqlite3.connect(banco) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM execucoes
            ORDER BY timestamp_inicio DESC
            LIMIT ?
            """,
            (limite,),
        )
        return [dict(linha) for linha in cursor.fetchall()]


def obter_evidencias_execucao(run_id: str, caminho_banco: Optional[Path | str] = None) -> str:
    """Recupera o contexto documental retornado pelo MCP durante um `run_id` específico (D-024)."""
    banco = obter_caminho_banco(caminho_banco)
    if not banco.exists() or not run_id:
        return ""

    with sqlite3.connect(banco) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT metadados FROM execucoes WHERE run_id = ?", (run_id,))
        linha = cursor.fetchone()
        if linha and linha["metadados"]:
            try:
                meta = json.loads(linha["metadados"])
                evidencias = meta.get("evidencias_mcp", [])
                if isinstance(evidencias, list) and evidencias:
                    return "\n\n".join(str(e) for e in evidencias if e)
            except Exception:
                pass

        cursor.execute(
            "SELECT detalhes FROM spans WHERE run_id = ? AND tipo = 'tool_mcp' ORDER BY timestamp_inicio ASC",
            (run_id,),
        )
        partes = []
        for s in cursor.fetchall():
            try:
                det = json.loads(s["detalhes"] or "{}")
                if det.get("evidencia"):
                    partes.append(str(det["evidencia"]))
            except Exception:
                pass
        return "\n\n".join(partes)


def obter_resumo_estatistico(caminho_banco: Optional[Path | str] = None) -> dict[str, Any]:
    """Gera resumo agregado por padrão arquitetural (Padrão -> Médias de Latência, Custo e Tokens)."""
    banco = obter_caminho_banco(caminho_banco)
    if not banco.exists():
        return {}

    with sqlite3.connect(banco) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                padrao_arquitetural,
                COUNT(*) as total_execucoes,
                SUM(sucesso) as total_sucessos,
                AVG(latencia_total_ms) as latencia_media_ms,
                AVG(total_tokens) as tokens_medios,
                SUM(custo_usd) as custo_total_usd,
                SUM(custo_brl) as custo_total_brl,
                SUM(chamadas_mcp) as total_chamadas_mcp,
                SUM(chamadas_llm) as total_chamadas_llm
            FROM execucoes
            WHERE resposta_final NOT LIKE 'Resposta simulada%'
            GROUP BY padrao_arquitetural
            """
        )
        return {linha["padrao_arquitetural"]: dict(linha) for linha in cursor.fetchall()}


def salvar_avaliacao(dados_avaliacao: dict[str, Any], caminho_banco: Optional[Path | str] = None) -> str:
    """Salva o resultado de uma avaliação de qualidade/segurança no banco SQLite."""
    banco = inicializar_banco(caminho_banco)
    avaliacao_id = dados_avaliacao.get("avaliacao_id") or f"eval_{uuid.uuid4().hex[:12]}"
    
    with sqlite3.connect(banco) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO avaliacoes (
                avaliacao_id, run_id, fidelidade_score, relevancia_score,
                seguranca_rbac_score, houve_alucinacao, falha_seguranca,
                fatos_inventados, justificativa, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                avaliacao_id,
                dados_avaliacao["run_id"],
                float(dados_avaliacao.get("fidelidade_score", 0.0)),
                float(dados_avaliacao.get("relevancia_score", 0.0)),
                float(dados_avaliacao.get("seguranca_rbac_score", 1.0)),
                1 if dados_avaliacao.get("houve_alucinacao") else 0,
                1 if dados_avaliacao.get("falha_seguranca") else 0,
                json.dumps(dados_avaliacao.get("fatos_inventados", []), ensure_ascii=False),
                dados_avaliacao.get("justificativa", ""),
                dados_avaliacao.get("timestamp") or _agora_iso(),
            ),
        )
        conn.commit()

    return avaliacao_id


def listar_avaliacoes(limite: int = 100, caminho_banco: Optional[Path | str] = None) -> list[dict[str, Any]]:
    """Lista as avaliações mais recentes com detalhes das execuções associadas."""
    banco = obter_caminho_banco(caminho_banco)
    if not banco.exists():
        return []

    with sqlite3.connect(banco) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                a.*,
                e.padrao_arquitetural,
                e.pergunta,
                e.papel_usuario,
                e.resposta_final
            FROM avaliacoes a
            LEFT JOIN execucoes e ON a.run_id = e.run_id
            ORDER BY a.timestamp DESC
            LIMIT ?
            """,
            (limite,),
        )
        return [dict(linha) for linha in cursor.fetchall()]


def obter_metricas_qualidade(caminho_banco: Optional[Path | str] = None) -> dict[str, Any]:
    """Agrega métricas de fidelidade, alucinação e conformidade RBAC por padrão arquitetural."""
    banco = obter_caminho_banco(caminho_banco)
    if not banco.exists():
        return {}

    with sqlite3.connect(banco) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                e.padrao_arquitetural,
                COUNT(a.avaliacao_id) as total_avaliacoes,
                AVG(a.fidelidade_score) as fidelidade_media,
                AVG(a.relevancia_score) as relevancia_media,
                AVG(a.seguranca_rbac_score) as rbac_conformidade_media,
                AVG(a.houve_alucinacao) as taxa_alucinacao,
                AVG(a.falha_seguranca) as taxa_falha_seguranca
            FROM avaliacoes a
            JOIN execucoes e ON a.run_id = e.run_id
            WHERE e.resposta_final NOT LIKE 'Resposta simulada%'
            GROUP BY e.padrao_arquitetural
            """
        )
        return {linha["padrao_arquitetural"]: dict(linha) for linha in cursor.fetchall()}
