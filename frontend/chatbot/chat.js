import { CONFIG, janelaTxt } from '../config.js';
import { $, h, icon, cssVar, isMobile } from '../shared/dom.js';
import { cap } from '../shared/formato.js';
import { TIPOS, TIPO, PERIODOS, PER, QUANDO } from '../shared/vocabulario.js';
import { scrub } from '../shared/anonimizacao.js';
import { cellOf } from '../shared/grade.js';
import { areaName, searchBairros, findBairroInText } from '../shared/bairros.js';
import { S } from '../shared/estado.js';
import { Store } from '../shared/store.js';
import { showView } from '../shared/navegacao.js';
import { map, renderSelection, setLayer } from '../mapa/mapa.js';
import { focusCell } from '../mapa/lista-areas.js';
import { startPick } from '../mapa/selecao.js';
import { reportItem } from '../relatos/item-relato.js';
import { toggleFollow } from '../relatos/alertas.js';
import { showApoioOnMap } from '../apoio/camada-apoio.js';
import { heuristic, infoProvedorIA, extrairNoServidor } from './extracao.js';
import { pedeRota, entenderRota, geocodificar } from './rota-conversa.js';
import { startRoute, routeClick } from '../mapa/trajeto.js';
import { MODOS } from '../mapa/roteador.js';

/* ------------------------------------------------------------------ chat da Aurora */
export const Chat = {
  log: null, quick: null, draft: null, step: 'inicio', busy: false, aiOn: false, lastCell: null,
  init() {
    this.log = $('#chatLog'); this.quick = $('#chatQuick');
    const ta = $('#chatText');
    $('#chatForm').addEventListener('submit', e => { e.preventDefault(); this.submit(); });
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.submit(); } });
    ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(120, ta.scrollHeight) + 'px'; });
    this.start();
    this.setAI(!!infoProvedorIA().usaModelo);
  },
  setAI(on) { this.aiOn = on; const el = $('#aiState'); el.classList.toggle('on', on); el.textContent = on ? 'Texto livre com IA' : 'Texto livre: modo simples'; },
  newDraft() { return { tipos: [], cell: null, sug: null, quando: null, periodo: null, periodoAsked: false, texto: '', removidos: [], detalhesAsked: false, origem: 'chat' }; },
  bot(content, cls = '') {
    const m = h('div', { class: 'msg bot ' + cls });
    if (typeof content === 'string') m.textContent = content; else m.append(...[].concat(content));
    this.log.append(m); this.scroll(); return m;
  },
  me(text) { this.log.append(h('div', { class: 'msg me', text })); this.scroll(); },
  card(node) { const m = h('div', { class: 'msg card' }, node); this.log.append(m); this.scroll(); return m; },
  scroll() { requestAnimationFrame(() => { this.log.scrollTop = this.log.scrollHeight; }); },
  clearQuick() { this.quick.replaceChildren(); },
  options(list, grid = false) {
    this.clearQuick();
    const wrap = grid ? h('div', { class: 'qgrid' }) : this.quick;
    for (const o of list) wrap.append(h('button', { type: 'button', class: 'qr' + (o.primary ? ' primary' : '') + (o.quiet ? ' quiet' : ''), onclick: () => o.go() }, o.label));
    if (grid) this.quick.append(wrap);
  },
  start() {
    this.draft = this.newDraft(); this.step = 'inicio'; this.busy = false;
    this.log.replaceChildren(); this.clearQuick();
    this.bot([h('span', null, 'Oi! Eu sou a Aurora. Te ajudo a registrar uma situação em Rio Claro para alertar outras mulheres. Você escolhe o que compartilhar.'),
      h('span', { class: 'note', text: 'Este relato não é um boletim de ocorrência. Em emergência, ligue 190.' })]);
    this.menuInicial();
  },
  menuInicial() {
    this.options([
      { label: 'Registrar uma situação', primary: true, go: () => { this.me('Quero registrar uma situação'); this.askTipo(); } },
      { label: 'Traçar uma rota', go: () => this.formRota() },
      { label: 'Estou em perigo agora', go: () => { this.me('Estou em perigo agora'); this.emergency(false); } },
      { label: 'Onde buscar apoio', go: () => { this.me('Onde buscar apoio?'); this.support(); } }
    ]);
  },
  next() {
    const d = this.draft;
    if (!d.tipos.length) return this.askTipo();
    if (!d.cell) return this.askOnde();
    if (!d.quando) return this.askQuando();
    if (!d.periodo && !d.periodoAsked) return this.askPeriodo();
    if (!d.detalhesAsked) return this.askDetalhes();
    return this.review();
  },
  askTipo() {
    this.step = 'tipo';
    this.bot('Qual foi o tipo de situação? Pode escolher mais de uma.');
    const sel = new Set(this.draft.tipos), grid = h('div', { class: 'qgrid' });
    const go = h('button', { type: 'button', class: 'qr primary' }, 'Continuar');
    const upd = () => { go.disabled = !sel.size; };
    go.onclick = () => { if (!sel.size) return; this.draft.tipos = TIPOS.filter(t => sel.has(t.id)).map(t => t.id); this.me(this.draft.tipos.map(t => TIPO[t].label).join(', ')); this.next(); };
    for (const t of TIPOS) {
      const b = h('button', { type: 'button', class: 'qr' + (sel.has(t.id) ? ' on' : ''), 'aria-pressed': sel.has(t.id) ? 'true' : 'false' }, t.long || t.label);
      b.onclick = () => { if (sel.has(t.id)) sel.delete(t.id); else if (sel.size < CONFIG.tiposMax) sel.add(t.id); b.classList.toggle('on', sel.has(t.id)); b.setAttribute('aria-pressed', sel.has(t.id) ? 'true' : 'false'); upd(); };
      grid.append(b);
    }
    upd(); this.clearQuick(); this.quick.append(grid, go);
  },
  askOnde() {
    this.step = 'onde';
    const s = this.draft.sug;
    this.clearQuick();
    if (s) {
      this.bot('Pelo que você contou, foi perto de ' + s.nome + '. Posso marcar a área "' + areaName(s.cell) + '"?');
      S.selected = s.cell; renderSelection();
      this.quick.append(
        h('button', { type: 'button', class: 'qr primary', onclick: () => { this.draft.sug = null; this.setCell(s.cell, 'Sim, pode marcar'); } }, 'Sim, pode marcar essa área'),
        h('button', { type: 'button', class: 'qr', onclick: () => { this.draft.sug = null; this.pickOnMap(); } }, 'Prefiro marcar no mapa'),
        this.bairroSearch());
      return;
    }
    this.bot([h('span', null, 'Onde foi? Marque no mapa ou busque o bairro.'), h('span', { class: 'note', text: 'Eu guardo só a região, uma área de cerca de 150 m. Nunca o endereço.' })]);
    this.quick.append(h('button', { type: 'button', class: 'qr primary', onclick: () => this.pickOnMap() }, 'Marcar no mapa'), this.bairroSearch());
  },
  bairroSearch() {
    const wrap = h('div', { class: 'bsearch' });
    const inp = h('input', { type: 'search', id: 'bairroInput', placeholder: 'Ou busque o bairro (ex.: Bela Vista)', 'aria-label': 'Buscar bairro' });
    const ul = h('ul');
    inp.addEventListener('input', () => {
      ul.replaceChildren(); const q = inp.value.trim(); if (q.length < 2) return;
      const res = searchBairros(q).slice(0, 6);
      for (const b of res) ul.append(h('li', null, h('button', { type: 'button', onclick: () => { this.draft.sug = null; this.setCell(cellOf(b.lat, b.lng, true), b.nome); } }, b.nome)));
      if (!res.length) ul.append(h('li', { class: 'muted', style: 'font-size:14px;padding:6px 2px' }, 'Não achei esse bairro. Tente marcar no mapa.'));
    });
    wrap.append(inp, ul); return wrap;
  },
  pickOnMap() {
    showView('mapa');
    this.bot('Toque no mapa na área onde aconteceu.');
    startPick(id => { openChat(); this.setCell(id); });
  },
  setCell(id, via) {
    this.draft.cell = id; S.selected = id; renderSelection();
    this.me(via ? via : 'Marquei no mapa');
    this.bot('Anotado: ' + areaName(id) + '. No mapa aparece só essa região.');
    this.next();
  },
  askQuando() {
    this.step = 'quando';
    this.bot('Quando aconteceu?');
    this.options(Object.entries(QUANDO).map(([k, lbl]) => ({ label: cap(lbl), go: () => { this.draft.quando = k; this.me(cap(lbl)); this.next(); } })), true);
  },
  askPeriodo() {
    this.step = 'periodo';
    this.bot('E em que horário, mais ou menos?');
    const opts = PERIODOS.map(p => ({ label: p.long, go: () => { this.draft.periodo = p.id; this.draft.periodoAsked = true; this.me(p.long); this.next(); } }));
    opts.push({ label: 'Não lembro', quiet: true, go: () => { this.draft.periodoAsked = true; this.me('Não lembro'); this.next(); } });
    this.options(opts, true);
  },
  askDetalhes() {
    this.step = 'detalhes';
    const d = this.draft;
    if (d.texto) {
      const q = h('span', { style: 'display:block;margin:8px 0;font-style:italic' }); q.textContent = '“' + d.texto + '”';
      this.bot([h('span', null, 'Vou usar esta descrição, já sem dados pessoais:'), q, h('span', null, 'Quer manter?')]);
      this.options([
        { label: 'Manter', primary: true, go: () => { d.detalhesAsked = true; this.me('Manter'); this.next(); } },
        { label: 'Escrever outra', go: () => { d.texto = ''; d.removidos = []; this.me('Escrever outra'); this.askDetalhes(); } },
        { label: 'Publicar sem descrição', quiet: true, go: () => { d.texto = ''; d.removidos = []; d.detalhesAsked = true; this.me('Sem descrição'); this.next(); } }
      ]);
      return;
    }
    this.bot([h('span', null, 'Quer contar algo que ajude outras mulheres? É opcional.'),
      h('span', { class: 'note', text: 'Escreva abaixo. Evite nomes, telefones, placas e endereço exato: eu tiro o que escapar antes de publicar.' })]);
    this.options([{ label: 'Pular esta parte', quiet: true, go: () => { d.detalhesAsked = true; this.me('Pular'); this.next(); } }]);
    if (!isMobile()) $('#chatText').focus();
  },
  async submit() {
    const ta = $('#chatText'), text = ta.value.trim();
    if (!text || this.busy) return;
    ta.value = ''; ta.style.height = 'auto';
    this.me(text);
    /* pedido de rota no meio de um relato: larga o relato (e as sugestões dele) e volta ao início */
    if (pedeRota(text)) { this.draft = this.newDraft(); this.step = 'inicio'; return this.pedirRota(text); }
    if (this.step === 'fim' || this.step === 'inicio') this.draft = this.newDraft();
    if (this.step === 'onde') {
      const b = findBairroInText(text);
      if (b) { this.draft.sug = { cell: cellOf(b.lat, b.lng, true), nome: b.nome }; return this.askOnde(); }
    }
    if (this.step === 'detalhes') return this.processDetails(text);
    if (this.step === 'revisao') { this.draft.texto = ''; this.draft.removidos = []; this.bot('Vou usar o que você escreveu como nova descrição.'); return this.processDetails(text); }
    return this.understand(text);
  },
  /* "uma rota da Rua X até a Rua Y": procura os dois lugares no mapa e abre o trajeto */
  async pedirRota(text) {
    this.busy = true; this.menuInicial(); // troca as sugestões do relato pelo menu inicial
    const typing = this.bot('Entendendo o trajeto…', 'typing');
    const p = await entenderRota(text, this.aiOn);
    typing.remove(); this.busy = false;
    this.abrirRota(p);
  },
  /* acha os dois lugares no mapa e abre o trajeto; false se não achou algum */
  abrirRota(p) {
    const a = p.origem && geocodificar(p.origem), b = p.destino && geocodificar(p.destino);
    if (!a || !b) {
      const quais = [!a && (p.origem || 'o ponto de partida'), !b && (p.destino || 'o destino')].filter(Boolean).join(' e ');
      this.bot('Não consegui achar ' + quais + ' no mapa. Tente o nome da rua ou do bairro, como "Rua 7" ou "Bela Vista".');
      return false;
    }
    const modo = Object.hasOwn(MODOS, p.modo) ? p.modo : 'pe';
    this.bot('Certo: de ' + cap(a.nome) + ' até ' + cap(b.nome) + ' (' + MODOS[modo].nome.toLowerCase() + '). Mostrando no mapa. O ponto é o meio da rua, não um número exato.');
    showView('mapa'); closeChat(); map.invalidateSize();
    startRoute(); S.route.modo = modo;
    routeClick(L.latLng(a.lat, a.lng)); routeClick(L.latLng(b.lat, b.lng));
    return true;
  },
  /* "Traçar uma rota": partida e destino em dois campos, como num app de mapas */
  formRota() {
    this.me('Quero traçar uma rota');
    this.bot('Escreva de onde você sai e para onde vai: rua, avenida ou bairro, com ou sem número. Nada disso é guardado.');
    let modo = 'pe';
    const campo = (rot, ph) => h('div', { class: 'bsearch' }, h('input', { type: 'text', placeholder: ph, 'aria-label': rot, autocomplete: 'off' }));
    const ca = campo('Ponto de partida', 'Partida (ex.: Rua 7, Centro)'), cb = campo('Destino', 'Destino (ex.: Avenida 29, Bela Vista)');
    const ia = ca.firstChild, ib = cb.firstChild;
    const botoes = Object.entries(MODOS).map(([k, m]) => h('button', { type: 'button', class: 'qr' + (k === modo ? ' on' : ''), 'aria-pressed': k === modo ? 'true' : 'false', 'data-modo': k,
      onclick: () => { modo = k; for (const bt of botoes) { const on = bt.dataset.modo === k; bt.classList.toggle('on', on); bt.setAttribute('aria-pressed', on ? 'true' : 'false'); } } }, m.nome));
    const go = () => {
      const o = ia.value.trim(), d = ib.value.trim();
      if (!o || !d) { this.bot('Preencha a partida e o destino.'); return; }
      this.me('De ' + o + ' até ' + d);
      if (this.abrirRota({ origem: o, destino: d, modo })) this.menuInicial();
    };
    for (const i of [ia, ib]) i.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); go(); } });
    this.clearQuick();
    this.quick.append(ca, cb, h('div', { style: 'display:flex;gap:7px' }, ...botoes),
      h('button', { type: 'button', class: 'qr primary', onclick: go }, 'Traçar rota'),
      h('button', { type: 'button', class: 'qr quiet', onclick: () => this.menuInicial() }, 'Voltar'));
    if (!isMobile()) ia.focus();
  },
  async understand(text) {
    this.busy = true;
    const typing = this.aiOn ? this.bot('Lendo o que você escreveu…', 'typing') : null;
    const heur = heuristic(text);
    let res = this.aiOn ? await extrairNoServidor(text) : null; // sem modelo o texto não sai do aparelho
    if (typing) typing.remove();
    if (res && res.fromAI) { if (!res.bairro) res.bairro = heur.bairro; if (!res.tipos.length) res.tipos = heur.tipos; }
    else if (!res) res = heur;
    this.busy = false;
    if (res.urgente) this.emergency(true);
    const d = this.draft, got = [];
    if (res.tipos.length && !d.tipos.length) { d.tipos = res.tipos; got.push(res.tipos.map(t => TIPO[t].label).join(', ')); }
    if (res.quando && !d.quando) { d.quando = res.quando; got.push('aconteceu ' + QUANDO[res.quando]); }
    if (res.periodo && !d.periodo) { d.periodo = res.periodo; d.periodoAsked = true; got.push(PER[res.periodo].long); }
    if (res.descricao && !d.texto) { const sc = scrub(res.descricao); d.texto = sc.text.slice(0, CONFIG.textoMax); d.removidos = [...new Set([...(res.removidos || []), ...sc.removed])]; }
    if (res.fromAI) d.origem = 'chat-ia';
    if (res.bairro && !d.cell) { d.sug = { cell: cellOf(res.bairro.lat, res.bairro.lng, true), nome: res.bairro.nome }; got.push('perto de ' + res.bairro.nome); }
    if (res.resposta) this.bot(res.resposta);
    if (got.length) this.bot('Anotei: ' + got.join(' · ') + '. Agora faltam alguns detalhes.');
    else if (!res.resposta) this.bot('Obrigada por contar. Vou te fazer perguntas rápidas para organizar o relato.');
    this.next();
  },
  async processDetails(text) {
    this.busy = true;
    const d = this.draft;
    let texto = text.slice(0, 700), removidos = [];
    if (this.aiOn) {
      const t = this.bot('Revisando o texto para tirar dados pessoais…', 'typing');
      const res = await extrairNoServidor(text);
      t.remove();
      if (res && res.descricao) {
        texto = res.descricao; removidos = res.removidos; d.origem = 'chat-ia';
        if (res.urgente) this.emergency(true);
        if (!d.periodo && res.periodo) { d.periodo = res.periodo; d.periodoAsked = true; }
      }
    }
    const sc = scrub(texto);
    d.texto = sc.text.slice(0, CONFIG.textoMax); d.removidos = [...new Set([...removidos, ...sc.removed])]; d.detalhesAsked = true;
    this.busy = false;
    this.next();
  },
  review() {
    this.step = 'revisao';
    const d = this.draft;
    const r = { id: 'preview', tipos: d.tipos, cell: d.cell, quando: d.quando, periodo: d.periodo, texto: d.texto, criado: Date.now() };
    const box = h('div', { class: 'preview' }, h('h5', null, 'Como vai aparecer no mapa'), h('b', { text: areaName(d.cell) }), reportItem(r, { preview: true, tag: 'div' }));
    if (d.removidos.length) box.append(h('p', { class: 'removed' }, icon('shield', 'i sm'), 'Tirei do texto: ' + d.removidos.join(', ') + '.'));
    box.append(h('p', { class: 'muted', style: 'font-size:13px' }, 'Publicado sem nome, contato ou local exato. Fica visível no mapa por ' + janelaTxt() + '.'));
    this.bot('Confira antes de publicar:');
    this.card(box);
    this.clearQuick();
    const pub = h('button', { class: 'qr primary', type: 'button' }, 'Publicar relato');
    pub.onclick = () => this.publish(pub);
    const edit = (label, fn) => h('button', { class: 'qr quiet', type: 'button', onclick: fn }, label);
    this.quick.append(pub, h('div', { class: 'qgrid' },
      edit('Mudar tipo', () => { d.tipos = []; this.askTipo(); }),
      edit('Mudar local', () => { d.cell = null; d.sug = null; this.askOnde(); }),
      edit('Mudar horário', () => { d.quando = null; d.periodo = null; d.periodoAsked = false; this.askQuando(); }),
      edit('Mudar texto', () => { d.texto = ''; d.removidos = []; d.detalhesAsked = false; this.askDetalhes(); })));
  },
  async publish(btn) {
    btn.disabled = true; btn.textContent = 'Publicando…';
    const d = this.draft;
    const r = { v: 1, tipos: d.tipos, cell: d.cell, quando: d.quando, periodo: d.periodo || null, texto: scrub(d.texto).text.slice(0, CONFIG.textoMax), criado: Date.now(), origem: d.origem };
    try {
      await Store.addReport(r);
      this.lastCell = d.cell; this.done();
    } catch (e) {
      btn.disabled = false; btn.textContent = 'Publicar relato';
      const c = e && e.code;
      if (Store.mode === 'api') this.bot(c === 'invalid_argument' ? 'O servidor não aceitou algum dado do relato. Revise e tente de novo.' : 'Não consegui publicar agora. Tente de novo em instantes.');
      else this.bot(c === 'invalid_argument' ? 'Sua conta pode ver o mapa, mas não tem permissão para publicar relatos neste protótipo. Peça à equipe acesso de participação.'
        : c === 'quota_exceeded' ? 'O protótipo atingiu o limite de relatos guardados. Avise a equipe responsável.'
        : 'Não consegui publicar agora. Tente de novo em instantes.');
    }
  },
  done() {
    this.step = 'fim';
    this.bot([h('b', null, 'Relato publicado.'), ' Obrigada por avisar outras mulheres. Ele aparece no mapa por ' + janelaTxt() + '.']);
    S.period = 'todos'; S.tipo = 'todos'; setLayer('relatos');
    const cell = this.lastCell;
    this.options([
      { label: 'Ver no mapa', primary: true, go: () => { closeChat(); focusCell(cell); } },
      { label: 'Acompanhar esta área', go: () => { toggleFollow(cell, true); this.bot('Pronto. As novidades dessa área aparecem em Meus alertas.'); } },
      { label: 'Fazer um B.O. online', go: () => { this.me('Quero fazer um B.O. online'); this.boOnline(); } },
      { label: 'Onde buscar apoio', go: () => { this.me('Onde buscar apoio?'); this.support(); } },
      { label: 'Registrar outra situação', quiet: true, go: () => this.start() }
    ]);
  },
  emergency(auto) {
    const row = (n, l) => h('div', { class: 'num-row' }, h('div', null, h('strong', { class: 'num', text: n }), ' ', h('span', { text: l })),
      h('button', { class: 'btn sm', type: 'button', 'data-copy': n }, icon('copy', 'i sm'), 'Copiar'));
    this.card(h('div', { class: 'emerg' }, h('b', null, 'Se você está em perigo agora, peça ajuda:'),
      row('190', 'Polícia Militar'), row('180', 'Central de Atendimento à Mulher'), row('153', 'Guarda Civil Municipal'),
      h('span', { style: 'font-size:14px;color:var(--ink-2)' }, 'Se puder, vá para um lugar movimentado e iluminado e avise alguém de confiança.')));
    if (!auto) this.options([{ label: 'Registrar uma situação', go: () => this.askTipo() }, { label: 'Voltar ao início', quiet: true, go: () => this.start() }]);
  },
  support() {
    this.bot('Em Rio Claro, a Delegacia da Mulher fica na Av. 23, 1300, no Bairro do Estádio, e registra boletim e pedido de medida protetiva. Para conversar e ter acompanhamento, há o CREAS (Rua 6, 640) e a Secretaria da Mulher (Rua 7, 830, WhatsApp (19) 99956-3042). O 180 orienta 24 horas, de graça.');
    this.options([
      { label: 'Ver os pontos no mapa', primary: true, go: () => showApoioOnMap() },
      { label: 'Ver todos os contatos', go: () => { closeChat(); showView('apoio'); } },
      { label: 'Voltar', quiet: true, go: () => this.resume() }
    ]);
  },
  boOnline() {
    this.bot([h('span', null, 'O boletim de ocorrência pode ser feito pela internet, 24 horas, na Delegacia Eletrônica da Polícia Civil de SP. '),
      h('a', { href: 'https://www.delegaciaeletronica.policiacivil.sp.gov.br', target: '_blank', rel: 'noopener' }, 'Abrir o site da Polícia Civil'),
      h('span', { class: 'note', text: 'O relato na Aurora não é enviado à polícia.' })]);
    this.options([{ label: 'Voltar', quiet: true, go: () => this.resume() }]);
  },
  resume() { if (this.step === 'fim' || this.step === 'inicio') this.start(); else this.next(); }
};

export function relatar() {
  showView('mapa');
  openChat();
  if (Chat.step === 'fim') Chat.start(); // abre no menu inicial; o relato só começa quando a pessoa escolhe "Registrar uma situação"
}
export function openChat() {
  const c = $('#chat'); c.classList.remove('picking');
  if (isMobile()) { c.classList.add('open'); document.body.style.overflow = 'hidden'; }
  else if (c.animate && !matchMedia('(prefers-reduced-motion: reduce)').matches) c.animate([{ boxShadow: 'inset 0 0 0 3px ' + cssVar('--brand') }, { boxShadow: 'inset 0 0 0 0 transparent' }], { duration: 900 });
}
export function closeChat() { $('#chat').classList.remove('open'); document.body.style.overflow = ''; }
