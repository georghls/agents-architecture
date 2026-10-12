# Três padrões para a Fase 3

Todos respondem ao mesmo problema documental pelo mesmo contrato MCP. Os diagramas da Fase 1 produzidos pelo autor são a referência visual a anexar e conferir. Os fluxos abaixo são **esboços para implementação**, não reconstruções fiéis desses diagramas.

## Coordenador — direção LangGraph

Um coordenador recebe a pergunta, decide se deve consultar especialistas, reúne evidências e compõe uma resposta com citações. Esboço de `State`: pergunta, identidade confiável fora da mensagem do modelo, tarefa atual, evidências, resultados dos especialistas, erros e resposta. `Nodes`: interpretar, rotear, consultar via MCP, sintetizar, validar evidências. `Edges`: início → interpretar → roteamento condicional → tarefas → síntese → validação → fim. O grafo coordena o processo; não é necessário pôr LangGraph dentro de cada especialista. Verificar critérios de parada e limites de chamadas.

## Plano–Executor — direção LangGraph

O planejador produz três tarefas limitadas e verificáveis, executadas em paralelo. Cada executor usa um cliente MCP quando precisar de dados; os três clientes acessam o mesmo servidor MCP. O estado registra plano, resultados por tarefa, evidências e falhas, e reúne as saídas após a execução. Uma decisão condicional pode revisar o plano com limite explícito ou encerrar. Prevenir loops e comandos inventados; validar que o plano só usa capacidades disponíveis.

## Conversação em Grupo — direção AutoGen

Agentes com papéis definidos trocam mensagens e confrontam evidências em uma conversa de equipe. Fixar mecanismo de seleção de falante, condição de término, limite de turnos e custo, e uma regra de síntese final. Todo acesso documental passa pelo cliente MCP e pela mesma autorização. Conversas longas exigem política de contexto e registro de proveniência.

## Comparação controlada

| Controlar igualmente | Registrar por execução |
|---|---|
| Corpus/versões e permissões | Padrão, versão do código e configuração |
| Modelo(s), parâmetros e preços aplicáveis | Chamadas LLM/MCP, tokens, custo estimado |
| Perguntas, critérios e referências corretas | Tempo, evidências usadas, resposta e avaliação |
| Infraestrutura e condição de execução | Erros, retries, negações de acesso e conclusão |

Um padrão pode exigir número diferente de agentes; registre essa diferença e evite concluir que o padrão é a única causa do resultado. Inclua uma referência simples de recuperação/resposta se for útil avaliar se a complexidade multiagente acrescenta valor. Não tratar a mesma nota dada por um modelo como verdade definitiva: revisar amostras com rubrica e evidência humana.

## Leituras oficiais

- [LangGraph Graph API: State, Nodes e Edges](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [AutoGen AgentChat Teams](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html)

Consultar a documentação correspondente às versões efetivamente instaladas; nomes de classes podem mudar.
