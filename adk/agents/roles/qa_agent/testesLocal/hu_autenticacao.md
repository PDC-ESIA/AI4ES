# História de Usuário: Sistema de Autenticação

## Como um usuário do sistema
## Eu quero poder me autenticar de forma segura
## Para que eu possa acessar recursos protegidos

### Critérios de Aceitação:

1. ✅ **Registro de usuário**
   - Deve validar email com formato correto
   - Deve validar telefone brasileiro
   - Deve exigir senha forte (mínimo 60/100)
   - Não deve permitir usuários duplicados

2. ✅ **Login seguro**
   - Deve verificar credenciais corretamente
   - Deve bloquear após 3 tentativas falhas
   - Deve impedir login de usuários desativados
   - Deve gerar sessão válida

3. ✅ **Gestão de sessão**
   - Sessões devem expirar após 1 hora
   - Deve permitir logout
   - Deve renovar sessão automaticamente

4. ✅ **Autenticação de dois fatores**
   - Deve gerar código de 6 dígitos
   - Código deve expirar em 5 minutos
   - Deve verificar código corretamente

5. ✅ **Recuperação de senha**
   - Deve permitir solicitação por email
   - Deve gerar token de recuperação
   - Deve validar força da nova senha

6. ✅ **Validações de segurança**
   - Senha fraca: ❌ (0-59/100)
   - Senha aceitável: ✅ (60-79/100)  
   - Senha forte: ✅ (80-100/100)

### Cenários de Teste:

**Caminho Feliz (100% correto):**
1. Registrar usuário com dados válidos
2. Fazer login com sucesso
3. Verificar sessão válida
4. Realizar logout

**Caminho Misto (alguns passam):**
1. Tentar login com senha errada (falha)
2. Tentar login novamente com senha correta (sucesso)
3. Gerar código 2FA (sucesso)
4. Verificar com código errado (falha)
5. Verificar com código correto (sucesso)

**Caminho Triste (tudo falha):**
1. Tentar registrar com email inválido (falha)
2. Tentar registrar com telefone inválido (falha) 
3. Tentar registrar com senha fraca (falha)
4. Tentar login com usuário inexistente (falha)
5. Exceder tentativas de login (bloqueio)

### Dados de Teste:

**Usuários válidos:**
- Usuário: `joao.silva`, Senha: `SenhaForte123!`, Email: `joao@email.com`, Telefone: `(11) 99999-9999`
- Usuário: `maria.santos`, Senha: `MariaSecure456@`, Email: `maria@empresa.com`, Telefone: `(21) 98888-8888`
- Usuário: `admin`, Senha: `AdminSuper789#`, Email: `admin@system.com`, Telefone: `(31) 97777-7777`

**Usuário desativado:**
- Usuário: `inativo.user`, Senha: `Inativo123$`, Email: `inativo@test.com`, Telefone: `(41) 96666-6666`

**Senhas de teste:**
- ❌ `fraca` (muito curta)
- ❌ `senhasimples` (sem complexidade)  
- ✅ `Senha123` (aceitável)
- ✅ `SenhaForte123!` (forte)
- ✅ `A1b2C3d4E5f6G7h8!` (muito forte)

### Arquivos para Teste:
- `test_scenario.py` - Classe completa do sistema de autenticação
- `test_auth_system.py` - Testes pytest com 21 casos de teste
- `hu_autenticacao.md` - Esta documentação

**Para executar os testes:**
```bash
python -m pytest test_auth_system.py -v
python test_scenario.py
```