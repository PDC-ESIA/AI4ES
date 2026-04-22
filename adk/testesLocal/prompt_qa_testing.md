# OBJETIVO
Gerar testes pytest automatizados completos para a classe `SistemaAutenticacao` baseado no código fonte e nos requisitos da HU.

## ARQUIVOS DE ENTRADA
1. **Código Fonte**: `test_scenario.py` - Classe completa do sistema de autenticação
2. **Requisitos**: `hu_autenticacao.md` - História de usuário com critérios de aceitação e cenários
j
## TAREFA
Analisar ambos os arquivos e gerar um arquivo pytest completo (`test_autenticacao_auto.py`) com:

### 1. ANÁLISE DO CÓDIGO
- Extrair todos os métodos públicos da classe
- Identificar parâmetros e retornos
- Compreender a lógica de negócio

### 2. ANÁLISE DOS REQUISITOS  
- Mapear critérios de aceitação para testes
- Identificar cenários de teste (feliz, misto, triste)
- Extrair dados de teste da HU

### 3. GERAÇÃO DE TESTES
Criar testes pytest que cubram:

**TESTES UNITÁRIOS (por método):**
- `registrar_usuario()` - validações, sucesso, falhas
- `login()` - credenciais corretas/incorretas, bloqueio
- `verificar_sessao()` - válida, expirada, inexistente  
- `logout()` - remoção de sessão
- `gerar_codigo_2fa()` - geração e expiração
- `verificar_2fa()` - código correto/incorreto
- `solicitar_recuperacao_senha()` - email válido/inválido
- `redefinir_senha()` - token válido/inválido
- Funções de validação (`validar_email`, `validar_telefone`, `calcular_forca_senha`)

**TESTES DE INTEGRAÇÃO (cenários):**
- **Caminho Feliz**: Registro → Login → Sessão → Logout
- **Caminho Misto**: Login falha → Login sucesso → 2FA
- **Caminho Triste**: Validações falham consecutivamente

**TESTES DE SEGURANça:**
- Bloqueio por tentativas excessivas
- Expiração de sessões e tokens
- Validação de força de senha

### 4. CRITÉRIOS DE QUALIDADE
- ✅ 100% de cobertura dos métodos públicos
- ✅ Todos os critérios de aceitação testados  
- ✅ Cenários positivos e negativos
- ✅ Asserts específicos e descritivos
- ✅ Mensagens de erro validadas
- ✅ Dados de teste da HU utilizados
- ✅ Fixtures para setup e tearDown

### 5. FORMATO DE SAÍDA
Arquivo `test_autenticacao_auto.py` contendo:
```python
"""
Testes automatizados para SistemaAutenticacao
Gerado automaticamente baseado em código e requisitos
"""
import pytest
import time
from test_scenario import SistemaAutenticacao

# Fixtures
@pytest.fixture
def sistema():
    return SistemaAutenticacao()

@pytest.fixture  
def sistema_com_dados(sistema):
    # Setup com dados da HU
    return sistema

# Testes unitários
# Testes de integração
# Testes de cenários
```

## DADOS DE TESTE DA HU
**Usuários válidos:**
- `joao.silva` / `SenhaForte123!` / `joao@email.com` / `(11) 99999-9999`
- `maria.santos` / `MariaSecure456@` / `maria@empresa.com` / `(21) 98888-8888` 
- `admin` / `AdminSuper789#` / `admin@system.com` / `(31) 97777-7777`

**Usuário desativado:**
- `inativo.user` / `Inativo123$` / `inativo@test.com` / `(41) 96666-6666`

**Senhas de teste:**
- ❌ `fraca` (0/100)
- ❌ `senhasimples` (30/100)
- ✅ `Senha123` (62/100)  
- ✅ `SenhaForte123!` (80/100)
- ✅ `A1b2C3d4E5f6G7h8!` (80/100)

## INSTRUÇÕES FINAIS
1. Analisar profundamente ambos os arquivos
2. Gerar testes completos e robustos
3. Validar que todos os requisitos estão cobertos
4. Garantir que os testes executem sem erros
5. Entregar arquivo pronto para execução

O resultado deve ser voce gerar os testes, testar e trazer o resultado.