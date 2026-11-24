import { h, toast } from '../shared/dom.js';
import { apiGet, apiPost } from '../shared/api.js';
import { Store } from '../shared/store.js';

const CAB = { 'X-Aurora-Equipe': '1' };
const papelNome = papel => papel === 'administrador' ? 'Administrador' : 'Moderador';

export function renderEquipe(el, usuario) {
  const lista = h('div', { class: 'equipe-lista', 'aria-live': 'polite' });
  const erro = h('p', { class: 'form-error', role: 'alert' });
  const login = h('input', { id: 'novo-login', required: true, minlength: 3, maxlength: 64,
    pattern: '[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}', autocomplete: 'off', placeholder: 'Ex.: ana.silva' });
  const senha = h('input', { id: 'nova-senha', type: 'password', required: true, minlength: 12, maxlength: 128, autocomplete: 'new-password' });
  const papel = h('select', { id: 'novo-papel' }, h('option', { value: 'moderacao' }, 'Moderador'), h('option', { value: 'administrador' }, 'Administrador'));
  const cadastrar = h('button', { class: 'btn primary', type: 'submit' }, 'Cadastrar pessoa');
  const mensagemErro = err => {
    if ([401, 403].includes(err.status)) Store.limparAcesso();
    erro.textContent = err.message || 'Não foi possível concluir. Tente novamente.';
  };
  async function carregar() {
    const pessoas = await apiGet('/usuarios/equipe');
    if (!el.contains(lista)) return;
    lista.replaceChildren();
    for (const pessoa of pessoas) {
      const status = h('span', { class: pessoa.ativo ? 'badge-ok' : 'badge-soft' }, pessoa.ativo ? 'Ativo' : 'Desativado');
      const detalhes = h('div', null, h('b', null, pessoa.login, pessoa.id === usuario.id ? ' (você)' : ''),
        h('p', { class: 'muted' }, papelNome(pessoa.papel)));
      const acoes = h('div', { class: 'acts' }, status);
      if (pessoa.papel !== 'administrador') acoes.append(h('button', { class: 'btn sm', type: 'button', onclick: async e => {
        const botao = e.currentTarget; botao.disabled = true; erro.textContent = '';
        try {
          await apiPost('/usuarios/equipe/' + encodeURIComponent(pessoa.id) + '/ativo', { ativo: !pessoa.ativo }, CAB);
          await carregar(); toast(pessoa.ativo ? 'Acesso desativado.' : 'Acesso reativado.');
        } catch (err) { mensagemErro(err); } finally { botao.disabled = false; }
      } }, pessoa.ativo ? 'Desativar' : 'Reativar'));
      lista.append(h('div', { class: 'equipe-pessoa' }, detalhes, acoes));
    }
  }
  const form = h('form', { class: 'card equipe-form', onsubmit: async e => {
    e.preventDefault(); cadastrar.disabled = true; erro.textContent = '';
    try {
      await apiPost('/usuarios/equipe', { login: login.value, senha: senha.value, papel: papel.value }, CAB);
      form.reset(); await carregar(); toast('Pessoa cadastrada. Ela já pode entrar com a própria conta.');
    } catch (err) { mensagemErro(err); } finally { cadastrar.disabled = false; }
  } }, h('h2', null, 'Adicionar à equipe'),
  h('p', { class: 'muted' }, 'Cada pessoa terá seu próprio acesso.'),
  h('label', { for: 'novo-login' }, 'Usuário da nova pessoa'), login,
  h('label', { for: 'nova-senha' }, 'Senha da nova pessoa'), senha,
  h('small', { class: 'muted' }, 'Mínimo de 12 caracteres. Entregue a senha à pessoa por um canal privado.'),
  h('label', { for: 'novo-papel' }, 'Permissão'), papel,
  h('p', { class: 'muted' }, 'Moderador revisa relatos. Administrador também gerencia a equipe.'), erro, cadastrar);
  const atualizar = h('button', { class: 'btn sm', type: 'button', onclick: () => carregar().catch(mensagemErro) }, 'Atualizar equipe');
  el.append(h('div', { class: 'equipe-layout' }, form, h('section', { class: 'card equipe-membros' },
    h('div', { class: 'equipe-toolbar' }, h('h2', null, 'Pessoas cadastradas'), atualizar), lista)));
  carregar().catch(mensagemErro);
}
