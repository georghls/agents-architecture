# Relatório Técnico: Agente Conversação em Grupo (Group Chat Pattern)

**Projeto Acadêmico:** Engenharia de Software para IA: Arquitetura, Integração Segura e Operação de Sistemas Multi-Agentes (MCP e LLMOps)  
**Instituição:** UNICAMP  
**Módulo:** Fase 3 — Padrões Arquiteturais Multiagentes  
**Componente:** Arquitetura 3 — Padrão Conversação em Grupo (Microsoft AutoGen 0.4 + MCP)  
**Arquivos de Referência:**
- Implementação da Equipe: [`src/agentes/conversa_grupo.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/src/agentes/conversa_grupo.py)
- Integração e Ferramenta MCP: [`src/agentes/mcp_toolkit.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/src/agentes/mcp_toolkit.py)
- Servidor MCP e RBAC: [`src/mcp/server.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/src/mcp/server.py)
- Testes Automatizados: [`tests/test_conversa_grupo.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/tests/test_conversa_grupo.py)
- Testes de Demonstração Interativa: [`tests/teste_conversa_grupo.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/tests/teste_conversa_grupo.py)
- Registro de Decisões: [`docs/decisions.md`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/decisions.md) (D-007, D-010, D-011, D-013 e D-014)
- Diagrama Conceitual da Fase 1: [`docs/diagramas/conversacao-em-grupo.mmd`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/diagramas/conversacao-em-grupo.mmd)

---

## 1. Visão Geral e Motivação

O padrão **Conversação em Grupo (*Group Chat*)** é a terceira arquitetura multiagente implementada e avaliada neste estudo dirigido. Enquanto o *Coordenador* e o *Plano–Executor* foram implementados sobre o framework **LangGraph** (modelando o fluxo cognitivo como Máquinas de Estado e grafos dirigidos), a *Conversação em Grupo* foi desenvolvida sobre o **Microsoft AutoGen 0.4+**, permitindo a comparação experimental entre os dois maiores paradigmas da indústria:
1. **Paradigma de Grafos/Máquinas de Estado (LangGraph):** Fluxos determinísticos, pipelines lineares ou paralelos (Fan-Out/Fan-In).
2. **Paradigma Conversacional/Atores Sociais (AutoGen):** Equipes colaborativas com personas heterogêneas debatendo e auditando informações até atingir consenso e aprovação.

### Comparativo Dimensional entre os Três Padrões

| Dimensão | 1. Coordenador (Supervisor) | 2. Plano–Executor | 3. Conversação em Grupo (Group Chat) |
|---|---|---|---|
| **Framework Base** | LangGraph | LangGraph | Microsoft AutoGen 0.4+ |
| **Paradigma** | Grafo Direcionado Centralizado | Map-Reduce / Fan-Out / Fan-In | Sociedade de Agentes Conversacionais |
| **Estratégia de Busca** | Reativa (1 busca direta por turno) | Proativa (decompõe em 1 a 3 tarefas paralelas) | Sequencial e deliberativa em sala de reunião |
| **Acesso ao MCP** | Pesquisador isolado via LangChain Tool | 1 a 3 executores simultâneos via LangChain Tool | Único: `retrieval_agent` via AutoGen FunctionTool |
| **Mecanismo de Controle** | Roteamento condicional no grafo | Borda condicional de distribuição (Send API) | Revezamento `RoundRobinGroupChat` + `TERMINATE` |
| **Auditoria / Validação** | Implícita no nó Redator | Implícita no nó Sintetizador | Explícita: `validator_agent` dedicado à auditoria |

---

## 2. Arquitetura da Conversação em Grupo

O fluxo visual implementado segue rigorosamente o desenho arquitetural homologado na Fase 1 (`conversacao-em-grupo.mmd`).

### 2.1. Diagrama de Fluxo e Componentes (Mermaid)

```mermaid
flowchart TB
    U(["Usuário / Aplicação Externa"]) -->|Pergunta + Role Seguro| G

    subgraph AG ["Microsoft AutoGen 0.4 (src/agentes/conversa_grupo.py)"]
        direction TB
        G["Group Chat Manager\n(RoundRobinGroupChat)"]
        
        R["Retrieval Agent\n(Único com Tool MCP)"]
        A["Analyst Agent\n(Síntese Documental)"]
        V["Validator Agent\n(Auditoria & 'TERMINATE')"]

        G -->|Turno 1: Investigar| R
        R -->|Turno 2: Evidências| A
        A -->|Turno 3: Síntese| V
        V -->|Aprovação ou Ajuste| G
    end

    subgraph MCP_BRIDGE ["Camada de Integração Segura MCP (stdio)"]
        R -->|buscar_documentos_corporativos\n(Token JWT assinado HS256)| M["Servidor MCP (src/mcp/server.py)"]
        M --> DB[("Supabase pgvector / PostgreSQL")]
    end
```

### 2.2. As Três Personas Especializadas

1. **`retrieval_agent` (Agente de Recuperação):**
   - **Responsabilidade:** Único agente da sala munido com a ferramenta de busca corporativa.
   - **Comportamento:** Formula a consulta sintética, invoca a ferramenta MCP assíncrona e relata fielmente os trechos documentais encontrados para o grupo.
   - **Regra de Falha Fechada:** Se o MCP retornar ausência de documentos ou erro de acesso, declara expressamente a ausência ao grupo sem inventar fatos.

2. **`analyst_agent` (Analista Corporativo):**
   - **Responsabilidade:** Sintetizar os trechos documentais trazidos pelo `retrieval_agent` em uma resposta clara, objetiva e polida para o usuário.
   - **Comportamento:** Não possui ferramentas externas. Apoia-se estritamente nas evidências documentadas. Se o Recuperador indicar falta de acesso, comunica educadamente a indisponibilidade de registros corporativos.

3. **`validator_agent` (Validador e Auditor Corporativo):**
   - **Responsabilidade:** Auditoria de qualidade, consistência factual e segurança.
   - **Comportamento:** Examina se a resposta do Analista não contém alucinações nem dados extrapolados além do que o MCP forneceu. Se a resposta for aprovada, emite a palavra-chave de controle **`TERMINATE`**, encerrando a conversa imediatamente. Se houver divergência, aponta correções.

---

## 3. Decisões Arquiteturais e Governança

### 3.1. Orquestração Sequencial: Round-Robin vs Selector (D-013)
Optou-se pelo `RoundRobinGroupChat` em vez do `SelectorGroupChat`:
- **Economia de Recursos:** O *Selector* exige uma chamada extra de LLM a cada turno apenas para decidir quem fala. O *Round-Robin* elimina essa sobrecarga, economizando ~50% dos tokens e das requisições.
- **Previsibilidade:** Garante a ordem lógica obrigatória para o domínio corporativo: primeiro busca (`Retrieval`), depois sintetiza (`Analyst`) e finalmente audita (`Validator`).
- **Prevenção de Loops:** Reduz drasticamente a latência e o risco de consumo de cotas de API.

### 3.2. Blindagem Criptográfica RBAC via JWT (D-010, D-011)
- O schema da ferramenta exposto aos agentes pelo AutoGen contém **apenas o argumento `query`**.
- O parâmetro `role` (`geral` ou `diretoria`) é capturado da sessão do usuário e assinado criptograficamente em um token JWT com algoritmo **HS256** (`src/autorizacao/tokens.py`), sendo injetado no ambiente do subprocesso (`MCP_AUTH_TOKEN`).
- Nenhum agente ou modelo consegue alterar privilégios por *prompt injection*.

### 3.3. Dupla Interface de Execução: Assíncrona e Síncrona (D-014)
- **`executar_conversa_grupo_async(...)`:** Interface nativa baseada em `asyncio` para serviços concorrentes de alto desempenho (ex.: FastAPI, streaming de tokens).
- **`executar_conversa_grupo(...)`:** Fachada síncrona de conveniência que encapsula o loop de eventos, permitindo invocação em uma única linha em scripts de terminal, suítes de teste e na futura interface visual (Streamlit), evitando erros de concorrência de loop.
- **Gestão de Ciclo de Vida HTTP:** Implementação de fechamento gracioso (`await cliente.close()`) no bloco `finally`, eliminando advertências de sockets pendentes no Windows ProactorEventLoop.

---

## 4. Evidências de Testes e Validação Experimental

### 4.1. Testes Automatizados Determinísticos
Arquivo: [`tests/test_conversa_grupo.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/tests/test_conversa_grupo.py)

```powershell
python -m pytest tests/test_conversa_grupo.py -m "not llm" -v
```

| Teste | Critério Verificado | Resultado |
|---|---|---|
| `test_equipe_possui_exatamente_tres_agentes_na_ordem_roundrobin` | Ordem estrita: Retrieval -> Analyst -> Validator | ✅ Passou |
| `test_apenas_retrieval_agent_possui_ferramenta_mcp` | Isolamento de tools: Analyst e Validator possuem 0 ferramentas | ✅ Passou |
| `test_criar_equipe_sem_role_lanca_excecao` | Falha fechada na ausência de papel (vazio, espaço ou None) | ✅ Passou |
| `test_extracao_resposta_final_prioriza_analista` | Extrai a síntese do analista limpando marcadores de controle | ✅ Passou |
| `test_extracao_resposta_final_fallback_validador` | Fallback seguro para o validador se o analista não emitir texto | ✅ Passou |
| `test_execucao_com_cliente_simulado` | Máquina de estados completa executada com dublê em 0 tokens | ✅ Passou |

**Resultado:** `8 passed in 4.82s`.

---

### 4.2. Teste de Integração Real com Supabase e Gemini
Arquivo: [`tests/test_conversa_grupo.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/tests/test_conversa_grupo.py) (marcador `llm`)

```powershell
python -m pytest tests/test_conversa_grupo.py -k "test_llm_geral_nao_vaza_projeto_secreto" -v
```

- **Cenário:** Pergunta sobre o Projeto Secreto de R$ 50 milhões com `papel="geral"`.
- **Comportamento Observado:** O servidor MCP filtrou o documento sigiloso, o `retrieval_agent` reportou a ausência, o `analyst_agent` comunicou a inexistência de registros acessíveis e o `validator_agent` auditou e aprovou com `TERMINATE`.
- **Resultado:** **Passou em 26.54s** sem nenhum vazamento de dados.

---

### 4.3. Demonstração Interativa em Terminal
Arquivo: [`tests/teste_conversa_grupo.py`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/tests/teste_conversa_grupo.py)

Execute a demonstração completa:
```powershell
python tests/teste_conversa_grupo.py
```

O script demonstra em tempo real os 3 cenários de homologação:
1. Perfil Geral vs Projeto Secreto (Falha fechada / Ausência de dados).
2. Perfil Diretoria vs Projeto Secreto (Recuperação do orçamento de R$ 50M e validação formal).
3. Perfil Geral vs Cardápio Corporativo (Recuperação da feijoada de segunda-feira sem alucinações sobre sexta-feira).

---

## 5. Conclusão da Fase 3

Com a conclusão e homologação da **Conversação em Grupo**, os três padrões arquiteturais definidos no planejamento original do estudo dirigido estão plenamente implementados, testados e conectados ao mesmo servidor MCP e à mesma base de dados vetorial:
- ✅ **Padrão 1: Coordenador** (LangGraph) — [`docs/agentes/coordenador.md`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/agentes/coordenador.md)
- ✅ **Padrão 2: Plano–Executor** (LangGraph) — [`docs/agentes/plano_executor.md`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/agentes/plano_executor.md)
- ✅ **Padrão 3: Conversação em Grupo** (Microsoft AutoGen) — [`docs/agentes/conversa_grupo.md`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/agentes/conversa_grupo.md)

O repositório encontra-se pronto para avançar para a **Fase 4: Observabilidade e LLMOps**.
