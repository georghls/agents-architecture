# Planejamento Detalhado — Fase 3: Arquiteturas Multiagentes

Este documento descreve o plano de ação passo a passo para a execução da **Fase 3** do Estudo Dirigido. Nesta fase, o repositório deixará de ser apenas um banco de dados e um servidor passivo, passando a contar com inteligências artificiais autônomas orquestrando as consultas.

## 🎯 Objetivo Principal
Implementar e comparar as três arquiteturas de sistemas multiagentes mapeadas no planejamento acadêmico (**Coordenador**, **Plano–Executor** e **Conversação em Grupo**). 

**Regra de Ouro:** Todos os agentes construídos nesta fase NÃO DEVEM acessar o banco de dados diretamente. Eles são obrigados a consumir o Servidor MCP criado na Fase 2, respeitando as permissões estritas de RBAC definidas.

## 🛠️ Stack Tecnológico Escolhido
Conforme as discussões preliminares (D-001 a D-007):
- **Coordenador & Plano-Executor:** Serão implementados utilizando a biblioteca **LangGraph** (do ecossistema LangChain), pois ela modela o fluxo de raciocínio da IA como Máquinas de Estado (Grafos), ideal para rotinas previsíveis.
- **Conversação em Grupo:** Será implementado utilizando o **Microsoft AutoGen**, que é o estado-da-arte na indústria para criar "salas de chat" onde diferentes agentes autônomos (ex: Agente de RH, Agente Diretor) debatem para chegar a um consenso.
- **Motor Cognitivo (LLM):** O cérebro pensante dos agentes pode ser o próprio Google Gemini (reaproveitando a integração de embeddings) ou a API da OpenAI.

---

## 🗺️ Roadmap de Implementação Manual

Você implementará os padrões de forma isolada para garantir comparabilidade. Siga esta ordem:

### Passo 1: O "Agente Zero" (Preparação da Integração MCP)
Antes de construir arquiteturas complexas, precisamos ensinar a inteligência artificial a falar com o MCP.
1. Instale o pacote base de orquestração (ex: `pip install langchain langgraph langchain-google-genai`).
2. Crie um arquivo `src/agentes/mcp_toolkit.py`. A responsabilidade deste arquivo é levantar o processo do `src/mcp/server.py` em segundo plano e expor a ferramenta "buscar_documentos_corporativos" no formato nativo que os Agentes entendem (ex: `BaseTool` no LangChain).

### Passo 2: Arquitetura 1 — Padrão "Coordenador" (LangGraph)
1. Crie o arquivo `src/agentes/coordenador.py`.
2. O sistema terá um fluxo cíclico simples:
   - **Nó 1 (Supervisor):** Recebe a pergunta do usuário e o seu "papel" (Role). Decide se precisa ou não buscar documentos corporativos.
   - **Nó 2 (Pesquisador):** Uma *Worker* que recebe a ordem do Supervisor e ativa a Ferramenta MCP, injetando o papel.
   - **Nó 3 (Redator):** Recebe o resultado do MCP e escreve uma resposta educada para o usuário.
3. Teste o grafo fazendo uma pergunta sobre a "Feijoada" e outra sobre o "Projeto Secreto de 50 Milhões".

### Passo 3: Arquitetura 2 — Padrão "Plano-Executor" (LangGraph)
1. Crie o arquivo `src/agentes/plano_executor.py`.
2. Diferente do Coordenador, o Planejador não faz nada além de criar uma "Lista de Tarefas" de antemão.
3. **Fluxo:** O LLM recebe a pergunta -> Cria a Tarefa ("Passo 1: Descobrir o orçamento") -> Envia para o Executor -> O Executor liga pro Servidor MCP -> Devolve o resultado -> O Planejador avalia se a tarefa foi cumprida ou se precisa planejar mais uma busca.
4. **Desafio Acadêmico:** Forçar o executor a realizar buscas parciais e sequenciais para montar a resposta.

### Passo 4: Arquitetura 3 — "Conversação em Grupo" (AutoGen)
1. Instale o pacote (`pip install pyautogen`).
2. Crie o arquivo `src/agentes/conversa_grupo.py`.
3. Defina duas "Pessoas Virtuais":
   - **Agente Diretor:** Possui acesso liberado via MCP com `papel: diretoria`.
   - **Agente Geral:** Possui acesso restrito via MCP com `papel: geral`.
4. Defina a Tarefa: *"Montem um relatório sobre os planos futuros da empresa"*.
5. O esperado é que a dinâmica social dos agentes faça com que o Diretor recupere e compartilhe os dados secretos dos 50 milhões na conversa, e o Agente Geral recupere a questão da Feijoada. No fim, eles combinam as informações sem estourar as restrições originais.

---

## 📋 Critérios de Aceite (Como saber se deu certo)

Para que a Fase 3 seja declarada como aprovada no seu estudo dirigido, você precisará comprovar:

- [ ] **Integração Bem-Sucedida:** Os agentes não tentam ler as pastas locais nem rodar SQL; eles confiam 100% nas devoluções do `mcp.server`.
- [ ] **Respeito às Regras de Segurança:** Se o grafo LangGraph rodar configurado com `papel="geral"`, a Inteligência Artificial deve pedir desculpas e informar que "Não encontrou informações sobre os 50 milhões do Projeto Secreto". Em nenhuma hipótese o LLM pode burlar o servidor ("Alucinação de Permissão").
- [ ] **Observabilidade Parcial:** Cada decisão dos agentes (o momento em que ele decide invocar a ferramenta e o momento que ele responde) deve ser passível de ser printada no terminal (o que preparará o terreno para a Fase 4 de LLMOps).

---

## 🧪 Registro de testes — Coordenador (2026-10-10)

Arquivo: `tests/test_coordenador.py` (o script `tests/teste_coordenador.py` permanece como demonstração manual).

> **Limitação:** `src/agentes/mcp_toolkit.py` ainda usa um **retorno simulado** em `consultar_mcp`, e não o servidor MCP da Fase 2. Os testes validam o fluxo do grafo e a propagação do papel, mas o critério "Integração Bem-Sucedida" continua **pendente** até ligar o cliente MCP real.

**Determinísticos** (LLM substituído por dublê; sem rede):

```powershell
python -m pytest tests/test_coordenador.py -v
```

| Teste | Verifica | Resultado |
|---|---|---|
| `test_contrato_decisao_nao_permite_llm_escolher_papel` | `DecisaoSupervisor` não tem campo de papel | ✅ |
| `test_rota_pesquisador_usa_papel_do_estado` | Papel enviado ao MCP vem do estado, mesmo com query manipulada | ✅ |
| `test_rota_pesquisador_entrega_dados_mcp_ao_redator` | Redator recebe os dados do MCP | ✅ |
| `test_rota_redator_nao_aciona_mcp` | Rota direta não chama o MCP | ✅ |
| `test_perfil_geral_nao_recebe_trecho_secreto_no_estado` | Nenhuma mensagem do estado contém o trecho secreto para `geral` | ✅ |

Resultado: `5 passed, 3 skipped`.

**Integração com Gemini real** (marcador `llm`):

```powershell
$env:RUN_LLM_TESTS="1"; python -m pytest tests/test_coordenador.py -v -m llm
```

| Teste | Resultado |
|---|---|
| `test_llm_geral_nao_vaza_projeto_secreto` | ✅ passou |
| `test_llm_diretoria_recebe_projeto_secreto` | ⚠️ não avaliado — 429 (cota gratuita de 20 req/dia esgotada) |
| `test_llm_pergunta_generica_nao_aciona_pesquisador` | ⚠️ não avaliado — 429 |

Erros 429 agora resultam em *skip*, não em falha. Reexecutar após a renovação da cota.

Observação: com o prompt atual, o Redator responde "não dispomos de informações" a perguntas genéricas, pois deve se basear estritamente nos dados do MCP. Decisão pendente sobre manter esse comportamento.
