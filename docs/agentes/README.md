# Módulo de Agentes — Fase 3

Esta pasta concentra os relatórios técnicos, especificações arquiteturais e documentação de implementação dos padrões multiagentes desenvolvidos para o estudo dirigido: **Engenharia de Software para IA: Arquitetura, Integração Segura e Operação de Sistemas Multi-Agentes (MCP e LLMOps)**.

## Padrões Arquiteturais

| Arquitetura | Framework | Documento | Status |
|---|---|---|---|
| **1. Coordenador (Supervisor Pattern)** | LangGraph | [`coordenador.md`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/agentes/coordenador.md) | Concluído e testado |
| **2. Plano–Executor** | LangGraph | [`plano_executor.md`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/agentes/plano_executor.md) | Concluído e testado |
| **3. Conversação em Grupo** | AutoGen | [`conversa_grupo.md`](conversa_grupo.md) | Concluído e testado |

## Regra Fundamental Compartilhada

Todos os agentes consomem a base de dados corporativa **exclusivamente por meio do Servidor MCP** via transporte `stdio`, preservando os limites de controle de acesso baseado em papel (RBAC) e as regras registradas em [`decisions.md`](file:///c:/Users/georg/Estudos/unicamp/agents-architecture/docs/decisions.md).
