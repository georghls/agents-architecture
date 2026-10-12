# Instruções para o Codex — Estudo Dirigido

## Contexto

Projeto acadêmico: **Engenharia de Software para IA: Arquitetura, Integração Segura e Operação de Sistemas Multi-Agentes (MCP e LLMOps)**. O cenário de estudo é um sistema de perguntas sobre documentos corporativos. Consulte `docs/estudo-dirigido.md` e o planejamento original em `docs/referencias/planejamento-original.pdf` antes de mudanças de escopo.

## Estado e prioridades

- Fase 1: desenho arquitetural visual concluído pelo autor; os diagramas ainda devem ser adicionados ao repositório e confrontados com a documentação.
- Fase 2: integração e segurança via MCP. Comece por uma implementação mínima verificável de dados, recuperação e controle de acesso; implemente o servidor e teste suas ferramentas com um cliente MCP, sem depender de agentes.
- Fases seguintes: três arquiteturas multiagentes, observabilidade/LLMOps, interface de usuário, dashboard e relatório técnico.
- Não declare uma fase concluída apenas porque existe documentação; registre os resultados dos testes de aceitação.

## Decisões e limites

- Padrões selecionados: **Coordenador**, **Plano–Executor** e **Conversação em Grupo**.
- Direção estudada: LangGraph para Coordenador e Plano–Executor; AutoGen para Conversação em Grupo. São escolhas de estudo; confira versões e compatibilidade antes da implementação.
- Para a comparação, use o mesmo corpus, regras de acesso, contrato MCP e conjunto de perguntas. Agentes acessam documentos por meio de clientes MCP, sem consultar diretamente o armazenamento de dados.
- A base pode conter armazenamento de originais, metadados e índice vetorial; a seleção concreta de fornecedores, linguagem, embedding, transporte MCP, identidade e infraestrutura permanece aberta. Consulte `docs/decisions.md`.
- O pipeline de ingestão é administrativo e pode falar diretamente com a camada de dados; a regra de acesso via MCP vale para consultas dos agentes.
- Não envie documentos reais sensíveis nem chaves ao repositório. Use dados sintéticos de teste quando necessário.
- Filtre permissões antes de retornar documentos, trechos ou metadados. Não aceite papel/permissão declarado pelo modelo como prova de identidade.

## Forma de trabalhar

1. Leia a documentação em `docs/`; identifique o menor incremento da fase atual.
2. Distingua **requisito do PDF**, **decisão de estudo** e **proposta ainda não aprovada**.
3. Antes de mudar contrato, stack ou fluxo, atualize `docs/decisions.md` com contexto, decisão e efeito; explique desvios do planejamento.
4. Mantenha módulos de ingestão, persistência, busca, autorização, MCP e agentes separados. Contratos de entrada e saída devem ser explícitos.
5. Acrescente testes úteis para isolamento entre perfis, recuperação, falhas e contratos MCP; execute-os e registre comandos e resultados.
6. Ao concluir uma tarefa, informe o que foi implementado, como rodar, evidências de teste e a próxima etapa.

## Documentos de apoio

- `docs/architecture.md`: componentes e fronteiras.
- `docs/mcp.md`: contratos propostos e segurança.
- `docs/multi-agent.md`: padrões e comparação.
- `docs/llmops.md`: observabilidade e avaliação.
- `docs/fase-2.md`: tarefas e critérios de aceite.
- `docs/decisions.md`: decisões confirmadas e pendências.
