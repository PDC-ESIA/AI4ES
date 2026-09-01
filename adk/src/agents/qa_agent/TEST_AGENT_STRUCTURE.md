# Estrutura operacional dos agentes de teste

Os três agentes seguem o mesmo fluxo:

```text
entrada → inspeção do projeto → seleção do perfil → geração → execução → relatório
```

## Unitário

- Perfis ativos: Python/FastAPI, Node/Express (JavaScript e TypeScript),
  Java/Spring e Go.
- Cada perfil define detector, gerador, executor e formato do resultado.

## Integração

- Base multistack orientada por perfis implementada.
- As mesmas quatro famílias estão registradas.
- Adaptadores ativos: pytest, runner Node declarado, JUnit/Maven ou Gradle e Go/testing.
- As saídas dos executores usam o mesmo envelope normalizado do QA.
- Perfis futuros também deverão declarar recursos e política de ambiente.

## E2E

- Base multistack orientada por perfis implementada.
- As mesmas quatro famílias estão registradas com Playwright TypeScript ativo.
- O gerador e executor são compartilhados; o runtime alvo continua condicionado
  a loopback ou a um inicializador local reconhecido.
- O retorno Playwright usa o mesmo envelope normalizado do QA.
- A matriz automatizada cobre os perfis de integração e E2E.
- Perfis futuros também deverão declarar superfície e política de ambiente.

## Contrato de resultado

Unitário, integração e E2E retornam os campos `status`, `tipo_teste`,
`inspecao`, `perfil`, `resumo`, `arquivos_gerados`, `detalhes` e `bloqueios`.
Integração e E2E também preservam logs e metadados originais em
`resultado_bruto` para auditoria e coleta de evidências.

## Reaproveitamento

A família vem primeiro do `tech_stack` entregue ao Coder; manifests são fallback.
Detecção, isolamento e contrato de resultado são compartilhados. Gerador,
ambiente e critério de sucesso continuam específicos de cada nível de teste.
