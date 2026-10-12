# Integração MCP e segurança

## Papel do servidor

O servidor oferece capacidades para buscar e recuperar conteúdo permitido, com contratos iguais para todos os padrões de agentes. Um **cliente MCP** na aplicação/orquestração invoca essas capacidades. O protocolo distingue *tools* (ações invocáveis) e *resources* (conteúdo identificado por URI); a primeira implementação pode usar tools e incluir resources apenas se houver um caso de uso claro.

As quatro ferramentas abaixo são um **contrato inicial proposto**, sujeito a revisão de tipos, paginação, limites e política de acesso antes de ser fixado. O incremento D-002 implementa somente `search_documents` e `get_document` com dados sintéticos em memória e saída estruturada; o restante do contrato e a persistência continuam pendentes.

| Ferramenta | Entrada sugerida | Saída sugerida | Garantia essencial |
|---|---|---|---|
| `search_documents` | `query`, `limit` e filtros permitidos | Trechos, IDs, referências e ordenação | Retornar somente evidências autorizadas |
| `get_document` | `document_id`, versão opcional | Conteúdo autorizado ou referência segura | Respeitar classificação e limite de tamanho |
| `get_document_metadata` | `document_id` | Metadados visíveis ao solicitante | Não vazar existência, título ou permissões indevidas |
| `list_documents` | Filtros e paginação | Resumo dos documentos visíveis | Aplicar autorização antes de listar |

Exemplo **ilustrativo de payload da aplicação**, não um envelope literal da especificação MCP:

```json
{
  "tool": "search_documents",
  "arguments": {"query": "Qual é a política de férias?", "limit": 5},
  "result": {
    "matches": [{"document_id": "doc-001", "version_id": "v1", "chunk_id": "c3", "excerpt": "...", "citation": "doc-001:v1:c3"}]
  }
}
```

O formato wire e a serialização exatos devem vir do SDK MCP fixado em `docs/decisions.md`.

## Segurança mínima testável

1. Identidade confiável: autenticar no limite da aplicação/transporte; evitar `user_role` passado pelo modelo como autoridade.
2. Autorização: aplicar política para leitura de conteúdo **e** metadados em cada ferramenta, inclusive na busca; negar por padrão.
3. Busca segura: filtrar documentos elegíveis antes de devolver resultados e verificar novamente no acesso por ID; cuidar de versões e exclusões.
4. Validação: limites de consulta, tamanho, paginação e IDs; mensagens de erro sem vazamento de dados.
5. Auditoria: registrar identidade técnica, decisão de acesso, ferramenta, IDs e tempo; não registrar trechos ou segredos em texto puro.
6. Segredos: guardar fora do repositório, usar princípio de menor privilégio e restringir quem pode ingerir ou revogar documentos.
7. Conteúdo recuperado é dado não confiável: instruções embutidas em PDFs não autorizam ações nem alteram políticas.

RBAC com perfis de exemplo (RH, Engenharia, externo) é uma proposta para testes, **não uma política corporativa real**. Definir matriz documento × papel e casos de negação antes de codificar. O transporte local (`stdio`) e o remoto (HTTP) têm modelos de credenciais diferentes; escolher um e seguir a especificação correspondente, sem presumir que um cabeçalho inventado basta.

## Aceitação isolada

- Um cliente MCP real descobre e chama as ferramentas implementadas.
- Dois perfis diferentes obtêm conjuntos distintos de documentos; um terceiro é negado sem vazamento por busca, listagem, metadados ou acesso por ID.
- Atualização/revogação impede recuperar versões antigas.
- Consulta válida recupera trecho rastreável; consulta sem evidência devolve vazio, sem inventar documento.
- Resultado, erros e auditoria passam pelos testes sem precisar iniciar qualquer agente.

## Referências de protocolo

- [Especificação MCP, versão 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [SDK Python 2.2.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0) e [autorização no SDK](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/run/authorization.md)

O SDK 2.2.0 também atende clientes de revisões anteriores; o cliente deste incremento negocia a revisão do protocolo ao conectar. Registrar a revisão efetivamente usada nas demonstrações.
