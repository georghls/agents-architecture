"""Módulo de autorização e controle de identidade.

No estágio atual (Fase 2 e Fase 3 - Coordenador), a autorização é realizada
diretamente pela filtragem de perfil (RBAC) via SQL no servidor MCP e pelo estado
imutável do orquestrador (`role`).

Este pacote está reservado para a futura expansão de políticas de acesso,
validação de tokens JWT/OAuth2 e desacoplamento de provedores de identidade
(conforme pendência A-05 em `docs/decisions.md`).
"""
