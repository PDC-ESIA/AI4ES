"""
Sistema de Autenticação Simulado para Testes QA
Esta classe simula um componente robusto de autenticação com vários métodos e cenários.
"""
import re
import hashlib
import time
from typing import Dict, Optional


class SistemaAutenticacao:
    """
    Sistema de autenticação robusto com múltiplos cenários de teste.

    Funcionalidades:
    - Registro de usuários com validações
    - Login com senha e autenticação de dois fatores
    - Gerenciamento de sessões
    - Recuperação de senha
    - Validação de força de senha
    - Limitação de tentativas
    """

    def __init__(self):
        self.usuarios = {}  # username -> {password_hash, email, telefone, ativo, tentativas_falhas}
        self.sessoes = {}  # session_id -> {username, expiracao}
        self.tokens_2fa = {}  # username -> {codigo, expiracao}
        self.tentativas_login = {}  # username -> ultima_tentativa, contador
        self.bloqueios = set()  # usuários temporariamente bloqueados

        # Configurações
        self.max_tentativas = 3
        self.tempo_bloqueio = 300  # 5 minutos
        self.expiracao_sessao = 3600  # 1 hora
        self.expiracao_2fa = 300  # 5 minutos

    def validar_email(self, email: str) -> bool:
        """Valida formato de email com regex robusto."""
        padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(padrao, email))

    def validar_telefone(self, telefone: str) -> bool:
        """Valida formato de telefone brasileiro."""
        # Remove caracteres não numéricos
        telefone_limpo = re.sub(r'\D', '', telefone)

        # Valida DDD (11-99) e número (8 ou 9 dígitos)
        if len(telefone_limpo) == 11:  # Com DDD e 9º dígito
            return telefone_limpo[:2] in ['11', '12', '13', '14', '15', '16', '17', '18', '19',
                                         '21', '22', '24', '27', '28', '31', '32', '33', '34',
                                         '35', '37', '38', '41', '42', '43', '44', '45', '46',
                                         '47', '48', '49', '51', '53', '54', '55', '61', '62',
                                         '63', '64', '65', '66', '67', '68', '69', '71', '73',
                                         '74', '75', '77', '79', '81', '82', '83', '84', '85',
                                         '86', '87', '88', '89', '91', '92', '93', '94', '95',
                                         '96', '97', '98', '99']
        elif len(telefone_limpo) == 10:  # Com DDD sem 9º dígito
            return telefone_limpo[:2] in ['11', '12', '13', '14', '15', '16', '17', '18', '19',
                                         '21', '22', '24', '27', '28', '31', '32', '33', '34',
                                         '35', '37', '38', '41', '42', '43', '44', '45', '46',
                                         '47', '48', '49', '51', '53', '54', '55', '61', '62',
                                         '63', '64', '65', '66', '67', '68', '69', '71', '73',
                                         '74', '75', '77', '79', '81', '82', '83', '84', '85',
                                         '86', '87', '88', '89', '91', '92', '93', '94', '95',
                                         '96', '97', '98', '99']
        return False

    def calcular_forca_senha(self, senha: str) -> int:
        """Calcula força da senha (0-100)."""
        if len(senha) < 8:
            return 0

        pontos = 0

        # Comprimento
        pontos += min(len(senha) * 4, 40)

        # Diversidade de caracteres
        if re.search(r'[a-z]', senha):
            pontos += 10
        if re.search(r'[A-Z]', senha):
            pontos += 10
        if re.search(r'\d', senha):
            pontos += 10
        if re.search(r'[^a-zA-Z\d]', senha):
            pontos += 10

        # Penalidades por padrões simples
        if senha.isdigit() or senha.isalpha():
            pontos -= 20
        if re.search(r'(.)\1{2,}', senha):  # Caracteres repetidos
            pontos -= 15

        return max(0, min(100, pontos))

    def hash_senha(self, senha: str) -> str:
        """Gera hash SHA-256 da senha com salt."""
        salt = "sistema_auth_2024"
        return hashlib.sha256(f"{salt}{senha}{salt}".encode()).hexdigest()

    def registrar_usuario(self, username: str, senha: str, email: str, telefone: str) -> Dict:
        """Registra novo usuário com validações."""
        # Validações
        if username in self.usuarios:
            return {"sucesso": False, "erro": "Usuário já existe"}

        if not self.validar_email(email):
            return {"sucesso": False, "erro": "Email inválido"}

        if not self.validar_telefone(telefone):
            return {"sucesso": False, "erro": "Telefone inválido"}

        forca_senha = self.calcular_forca_senha(senha)
        if forca_senha < 60:
            return {"sucesso": False, "erro": f"Senha muito fraca ({forca_senha}/100)"}

        # Registro
        self.usuarios[username] = {
            "password_hash": self.hash_senha(senha),
            "email": email,
            "telefone": telefone,
            "ativo": True,
            "tentativas_falhas": 0
        }

        return {"sucesso": True, "forca_senha": forca_senha}

    def verificar_bloqueio(self, username: str) -> Optional[str]:
        """Verifica se usuário está bloqueado."""
        if username in self.bloqueios:
            # Verifica se já passou o tempo de bloqueio
            tentativa_info = self.tentativas_login.get(username, {})
            ultima_tentativa = tentativa_info.get('ultima_tentativa', 0)

            if time.time() - ultima_tentativa >= self.tempo_bloqueio:
                self.bloqueios.remove(username)
                self.tentativas_login[username] = {'contador': 0, 'ultima_tentativa': time.time()}
                return None
            else:
                tempo_restante = int(self.tempo_bloqueio - (time.time() - ultima_tentativa))
                return f"Usuário bloqueado. Tente novamente em {tempo_restante} segundos"
        return None

    def login(self, username: str, senha: str) -> Dict:
        """Realiza login do usuário."""
        # Verifica bloqueio
        if bloqueio_msg := self.verificar_bloqueio(username):
            return {"sucesso": False, "erro": bloqueio_msg}

        # Verifica se usuário existe
        if username not in self.usuarios:
            return {"sucesso": False, "erro": "Usuário não encontrado"}

        usuario = self.usuarios[username]

        # Verifica se está ativo
        if not usuario["ativo"]:
            return {"sucesso": False, "erro": "Usuário desativado"}

        # Verifica senha
        senha_correta = usuario["password_hash"] == self.hash_senha(senha)

        # Atualiza tentativas
        tentativa_info = self.tentativas_login.get(username, {'contador': 0, 'ultima_tentativa': time.time()})

        if not senha_correta:
            tentativa_info['contador'] += 1
            tentativa_info['ultima_tentativa'] = time.time()
            self.tentativas_login[username] = tentativa_info

            if tentativa_info['contador'] >= self.max_tentativas:
                self.bloqueios.add(username)
                return {"sucesso": False, "erro": "Muitas tentativas falhas. Usuário bloqueado temporariamente"}

            return {"sucesso": False, "erro": "Senha incorreta", "tentativas_restantes": self.max_tentativas - tentativa_info['contador']}

        # Login bem-sucedido - reseta contador
        self.tentativas_login[username] = {'contador': 0, 'ultima_tentativa': time.time()}

        # Gera sessão
        session_id = hashlib.sha256(f"{username}{time.time()}".encode()).hexdigest()
        self.sessoes[session_id] = {
            "username": username,
            "expiracao": time.time() + self.expiracao_sessao
        }

        return {"sucesso": True, "session_id": session_id, "expiracao": self.expiracao_sessao}

    def verificar_sessao(self, session_id: str) -> Dict:
        """Verifica se sessão é válida."""
        if session_id not in self.sessoes:
            return {"valida": False, "erro": "Sessão não encontrada"}

        sessao = self.sessoes[session_id]

        if time.time() > sessao["expiracao"]:
            del self.sessoes[session_id]
            return {"valida": False, "erro": "Sessão expirada"}

        # Renova sessão se estiver perto de expirar
        if time.time() > sessao["expiracao"] - 300:  # 5 minutos antes
            sessao["expiracao"] = time.time() + self.expiracao_sessao

        return {"valida": True, "username": sessao["username"]}

    def logout(self, session_id: str) -> Dict:
        """Encerra sessão do usuário."""
        if session_id in self.sessoes:
            del self.sessoes[session_id]
            return {"sucesso": True}
        return {"sucesso": False, "erro": "Sessão não encontrada"}

    def gerar_codigo_2fa(self, username: str) -> Dict:
        """Gera código de autenticação de dois fatores."""
        if username not in self.usuarios:
            return {"sucesso": False, "erro": "Usuário não encontrado"}

        # Gera código de 6 dígitos
        codigo = str(int(hashlib.sha256(f"2fa{username}{time.time()}".encode()).hexdigest()[:6], 16) % 1000000).zfill(6)

        self.tokens_2fa[username] = {
            "codigo": codigo,
            "expiracao": time.time() + self.expiracao_2fa
        }

        return {"sucesso": True, "codigo": codigo, "expiracao": self.expiracao_2fa}

    def verificar_2fa(self, username: str, codigo: str) -> Dict:
        """Verifica código de autenticação de dois fatores."""
        if username not in self.tokens_2fa:
            return {"sucesso": False, "erro": "Nenhum código 2FA pendente"}

        token_info = self.tokens_2fa[username]

        if time.time() > token_info["expiracao"]:
            del self.tokens_2fa[username]
            return {"sucesso": False, "erro": "Código 2FA expirado"}

        if token_info["codigo"] != codigo:
            return {"sucesso": False, "erro": "Código 2FA incorreto"}

        del self.tokens_2fa[username]
        return {"sucesso": True}

    def solicitar_recuperacao_senha(self, email: str) -> Dict:
        """Solicita recuperação de senha."""
        # Encontra usuário pelo email
        usuario_encontrado = None
        for username, info in self.usuarios.items():
            if info["email"] == email:
                usuario_encontrado = username
                break

        if not usuario_encontrado:
            return {"sucesso": False, "erro": "Email não encontrado"}

        # Gera token de recuperação (simulado)
        token = hashlib.sha256(f"recovery{email}{time.time()}".encode()).hexdigest()[:20]

        return {"sucesso": True, "token": token, "username": usuario_encontrado}

    def redefinir_senha(self, token: str, nova_senha: str) -> Dict:
        """Redefine senha usando token de recuperação."""
        # Em um sistema real, validaria o token contra um banco
        # Aqui vamos simular que qualquer token é válido por 1 hora

        forca_senha = self.calcular_forca_senha(nova_senha)
        if forca_senha < 60:
            return {"sucesso": False, "erro": f"Nova senha muito fraca ({forca_senha}/100)"}

        # Simula busca por username baseado no token (em sistema real seria mapeamento token->username)
        # Para simplificar, assumimos que o token contém hint do username
        try:
            # Extrai hint do username do token (simulação)
            username_hint = token[:8]  # Primeiros 8 chars do token como hint
            usuario_encontrado = None

            for username in self.usuarios.keys():
                if username.startswith(username_hint):
                    usuario_encontrado = username
                    break

            if not usuario_encontrado:
                return {"sucesso": False, "erro": "Token inválido ou expirado"}

            # Atualiza senha
            self.usuarios[usuario_encontrado]["password_hash"] = self.hash_senha(nova_senha)

            # Reseta tentativas falhas
            self.usuarios[usuario_encontrado]["tentativas_falhas"] = 0
            if usuario_encontrado in self.bloqueios:
                self.bloqueios.remove(usuario_encontrado)

            return {"sucesso": True, "forca_senha": forca_senha}

        except:
            return {"sucesso": False, "erro": "Erro ao processar token"}


# Funções auxiliares para testes
def criar_cenario_teste() -> SistemaAutenticacao:
    """Cria sistema com dados de teste."""
    sistema = SistemaAutenticacao()

    # Usuários de teste
    sistema.registrar_usuario("joao.silva", "SenhaForte123!", "joao@email.com", "(11) 99999-9999")
    sistema.registrar_usuario("maria.santos", "MariaSecure456@", "maria@empresa.com", "(21) 98888-8888")
    sistema.registrar_usuario("admin", "AdminSuper789#", "admin@system.com", "(31) 97777-7777")

    # Usuário desativado
    sistema.registrar_usuario("inativo.user", "Inativo123$", "inativo@test.com", "(41) 96666-6666")
    sistema.usuarios["inativo.user"]["ativo"] = False

    return sistema


def executar_testes_completos():
    """Executa suite completa de testes."""
    print("=== SISTEMA DE AUTENTICAÇÃO - TESTES COMPLETOS ===\n")

    sistema = criar_cenario_teste()

    # Teste 1: Login bem-sucedido
    print("1. Login bem-sucedido:")
    resultado = sistema.login("joao.silva", "SenhaForte123!")
    print(f"   Resultado: {resultado}")

    # Teste 2: Login com senha incorreta
    print("\n2. Login com senha incorreta:")
    resultado = sistema.login("joao.silva", "senhaerrada")
    print(f"   Resultado: {resultado}")

    # Teste 3: Múltiplas tentativas falhas (bloqueio)
    print("\n3. Múltiplas tentativas falhas (bloqueio):")
    for i in range(3):
        resultado = sistema.login("maria.santos", "senhaerrada")
        print(f"   Tentativa {i+1}: {resultado}")

    # Teste 4: Login com usuário não existente
    print("\n4. Login com usuário não existente:")
    resultado = sistema.login("nao.existe", "qualquersenha")
    print(f"   Resultado: {resultado}")

    # Teste 5: Login com usuário desativado
    print("\n5. Login com usuário desativado:")
    resultado = sistema.login("inativo.user", "Inativo123$")
    print(f"   Resultado: {resultado}")

    # Teste 6: Verificação de sessão válida
    print("\n6. Verificação de sessão válida:")
    login_result = sistema.login("admin", "AdminSuper789#")
    if login_result["sucesso"]:
        sessao_result = sistema.verificar_sessao(login_result["session_id"])
        print(f"   Sessão: {sessao_result}")

    # Teste 7: Logout
    print("\n7. Logout:")
    if login_result["sucesso"]:
        logout_result = sistema.logout(login_result["session_id"])
        print(f"   Logout: {logout_result}")

    # Teste 8: Autenticação 2FA
    print("\n8. Autenticação 2FA:")
    # Primeiro gera código
    codigo_result = sistema.gerar_codigo_2fa("joao.silva")
    print(f"   Código gerado: {codigo_result}")

    if codigo_result["sucesso"]:
        # Tenta verificar (com código correto)
        verificacao_result = sistema.verificar_2fa("joao.silva", codigo_result["codigo"])
        print(f"   Verificação (código correto): {verificacao_result}")

        # Tenta verificar (com código errado)
        verificacao_result = sistema.verificar_2fa("joao.silva", "000000")
        print(f"   Verificação (código errado): {verificacao_result}")

    # Teste 9: Recuperação de senha
    print("\n9. Recuperação de senha:")
    recuperacao_result = sistema.solicitar_recuperacao_senha("joao@email.com")
    print(f"   Solicitação: {recuperacao_result}")

    if recuperacao_result["sucesso"]:
        redefinicao_result = sistema.redefinir_senha(
            recuperacao_result["token"],
            "NovaSenhaForte456!"
        )
        print(f"   Redefinição: {redefinicao_result}")

    # Teste 10: Validações de força de senha
    print("\n10. Validações de força de senha:")
    senhas_testes = [
        "fraca",           # Muito curta
        "senhasimples",    # Sem complexidade
        "Senha123",        # Fraca (só 8 chars)
        "SenhaForte123!",  # Forte
        "A1b2C3d4E5f6G7h8!"  # Muito forte
    ]

    for senha in senhas_testes:
        forca = sistema.calcular_forca_senha(senha)
        status = "✅" if forca >= 60 else "❌"
        print(f"   '{senha}': {forca}/100 {status}")

    print("\n=== FIM DOS TESTES ===")


if __name__ == "__main__":
    executar_testes_completos()