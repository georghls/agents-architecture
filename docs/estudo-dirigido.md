# Escopo do Estudo Dirigido

## Origem e estatuto

O documento `referencias/planejamento-original.pdf` define o tema, a justificativa, os objetivos, as cinco fases e os entregáveis. As escolhas de cenário, três padrões e frameworks vieram das conversas de planejamento; os detalhes de implementação são propostas a validar. Os diagramas visuais dos três padrões, produzidos pelo autor na Fase 1, foram transcritos em `diagramas/`; o desenho da arquitetura geral ainda não acompanha este pacote.

## Problema de estudo

Projetar, implementar e monitorar um sistema multiagente ligado a fontes de dados reais por MCP, com comunicação e gestão de estado, integração segura, observabilidade e interface de usuário. Para tornar o experimento comparável, o caso escolhido é responder perguntas sobre documentos corporativos usando trechos recuperados como evidência. Na prototipagem, use documentos sintéticos e rotule-os como tais; a adoção de dados reais exigirá permissão e governança.

Pergunta experimental proposta: **Como os padrões Coordenador, Plano–Executor e Conversação em Grupo diferem em qualidade, latência, custo e segurança ao responder à mesma base documental pelo mesmo MCP?** Esta formulação é uma operacionalização sugerida, não uma citação literal do PDF.

## Fases e marcos

| Fase | Conforme o planejamento original | Interpretação operacional para este projeto |
|---|---|---|
| 1. Desenho arquitetural | Mapear LangChain/AutoGen, MCP e LLMOps; desenhar diagramas | Autor informa ter concluído o fluxo visual; anexar diagramas e revisar consistência |
| 2. Integração e segurança — MCP | Backend, servidor MCP, políticas de acesso e integração ao banco | Corpus, ingestão, recuperação, autorização e ferramentas MCP testadas sem agentes |
| 3. Orquestração multiagentes | Lógica dos agentes, workflows e memória | Implementar os três padrões com o mesmo contrato MCP |
| 4. Observabilidade e LLMOps | Métricas de custo/latência e testes de resiliência | Coletar traces, avaliar respostas, falhas e apresentar dashboard |
| 5. Documentação | Análise de performance e relatório técnico | Comparar padrões, registrar gargalos, limitações e integração |

Instrumentação mínima deve ser pensada desde a Fase 2 para evitar medições irrecuperáveis; a avaliação sistemática e o dashboard pertencem à Fase 4.

## Entregáveis do PDF

- Repositório com código fonte.
- Dashboard de monitoramento com métricas das execuções.
- Relatório técnico com padrões arquiteturais escolhidos, gargalos e resultados da integração.
- Uma interface de usuário aparece nos objetivos específicos, embora não seja item independente na lista final de entregáveis. Planejar sua implementação em fase apropriada.

## Dicionário curto

- **MCP:** protocolo de comunicação entre clientes e servidores que expõem capacidades; não substitui autorização de acesso aos dados.
- **RAG:** recuperação de trechos relevantes antes da geração da resposta; embeddings são uma estratégia de indexação, não uma resposta garantida.
- **LLMOps:** observação, medição e avaliação do comportamento do sistema de IA ao longo das execuções.

## Evidência exigida no relatório

Versões e configuração, corpus e permissões, perguntas de teste, método de avaliação, execução por padrão, resultados, custos, limitações e ameaças à validade da comparação. Diferencie dados simulados de dados corporativos reais.
