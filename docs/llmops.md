# Observabilidade, avaliação e resiliência

## Instrumentação desde a Fase 2

Gerar um `run_id` por pergunta e ligar chamada da interface, execução do padrão, chamada MCP, busca e resposta. Guardar versão do corpus, configuração, horário, resultado, tempo e erro. Dados de usuário, trechos e prompts exigem minimização e política de retenção; métricas podem ser coletadas sem copiar conteúdo sensível para logs.

## Métricas para a Fase 4

| Medida | Definição operacional inicial |
|---|---|
| Latência | Tempo até resposta final e tempo por etapa; percentis sobre várias execuções |
| Tokens | Entrada e saída por chamada e total; registrar indisponibilidade quando provedor não informa |
| Custo | Estimativa por modelo/tabela de preços versionada, com moeda e data |
| Chamadas MCP | Total por ferramenta, erros, negações e retries |
| Recuperação | Cobertura da evidência esperada, documentos irrelevantes e acesso negado corretamente |
| Fidelidade | Afirmações relevantes sustentadas por trechos citados, com rubrica de revisão |
| Resposta | Correção, completude e capacidade de dizer “não sei” sem evidência |
| Segurança | Tentativas de acesso indevido bloqueadas em busca, metadados e documento |

Não use “score de similaridade = 0,92” como probabilidade de acerto, nem reduza alucinação a uma única porcentagem sem definir critério e amostra. Para comparar custos, registre versões e preços da época do experimento.

## Conjunto de avaliação

Criar perguntas com respostas e trechos de referência, perguntas ambíguas, respostas inexistentes, documentos conflitantes, diferentes perfis e tentativas de instruções maliciosas dentro do texto recuperado. Fixar corpus e perguntas antes de rodar os padrões; reportar quantidade, método de julgamento e incerteza. Executar mais de uma vez quando a geração não for determinística.

## Falhas a ensaiar

Timeout do servidor MCP, documento removido após indexação, erro de embedding, índice indisponível, token de acesso inválido, resultado vazio e limite de iterações. A resposta deve falhar de modo explícito e auditável, evitando inventar fontes.

## Dashboard e relatório

Exibir série temporal, percentis de latência, custo estimado, chamadas MCP/LLM, erros e qualidade por padrão. O relatório da Fase 5 deve incluir o método de medição, tabelas comparáveis, exemplos anonimizados, gargalos, limites e propostas de melhoria. A interface de perguntas é outro objetivo do planejamento e terá escopo próprio.
