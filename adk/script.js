// =======================
// Módulo de LocalStorage
// =======================
const LS_KEY = 'usuarios';

function getUsers() {
    try {
        const raw = localStorage.getItem(LS_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch (e) {
        // Corrupção ou JSON inválido
        return [];
    }
}

function saveUsers(users) {
    localStorage.setItem(LS_KEY, JSON.stringify(users));
}

function addUser({ nome, email, senha }) {
    if (!nome || !email || !senha) {
        return { ok: false, error: 'Preencha todos os campos.' };
    }
    const users = getUsers();
    if (users.some(u => u.email.toLowerCase() === email.toLowerCase())) {
        return { ok: false, error: 'Já existe um usuário cadastrado com este e-mail.' };
    }
    users.push({ nome, email, senha }); // senha como texto simples, não exibida
    saveUsers(users);
    return { ok: true };
}

// =======================
// Renderização
// =======================
function renderUsers() {
    const listDiv = document.getElementById('usersList');
    const users = getUsers();
    if (users.length === 0) {
        listDiv.innerHTML = '<h3>Usuários Cadastrados</h3><em>Nenhum usuário cadastrado ainda.</em>';
        return;
    }
    let html = '<h3>Usuários Cadastrados</h3>';
    html += users.map(u => `<div class="user-item"><b>${escapeHTML(u.nome)}</b><br><span class="user-email">${escapeHTML(u.email)}</span></div>`).join('');
    listDiv.innerHTML = html;
}

function showMessage(msg, tipo = 'erro') {
    // tipo: 'erro' ou 'sucesso'
    const div = document.getElementById('message');
    div.style.color = tipo === 'erro' ? '#c0392b' : '#107e13';
    div.textContent = msg || '';
}

function escapeHTML(str) {
    return str.replace(/[&<>"']/g, function (c) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c];
    });
}

// =======================
// Form Handling
// =======================
document.addEventListener('DOMContentLoaded', () => {
    renderUsers();
    document.getElementById('userForm').onsubmit = (e) => {
        e.preventDefault();
        showMessage('');
        const nome = document.getElementById('nome').value.trim();
        const email = document.getElementById('email').value.trim();
        const senha = document.getElementById('senha').value;
        const result = addUser({ nome, email, senha });
        if (!result.ok) {
            showMessage(result.error, 'erro');
            return;
        }
        showMessage('Cadastro realizado com sucesso!', 'sucesso');
        document.getElementById('userForm').reset();
        renderUsers();
    };
});
