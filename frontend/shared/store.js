/* armazenamento: relatos no servidor da Aurora (modo api) ou no aparelho (modo local).
   Votos, moderação e perfil ficam sempre no aparelho. */
import { CONFIG } from '../config.js';
import { LS } from './armazenamento-local.js';
import { MODO_DADOS } from './dados.js';
import { ApiErro, apiGet, apiPost, apiDelete } from './api.js';
import { toast } from './dom.js';

export const Store = {
  mode: 'local', ready: false, uid: null, canWrite: true, canEdit: false, papeis: [],
  reports: new Map(), votes: {}, myVotes: {}, mod: { oculto: {}, verificado: {} },
  perfil: { areas: [], meus: [], visto: 0 },
  subs: new Set(), queues: {}, apagados: new Set(), assinatura: null,
  on(f) { this.subs.add(f); },
  emit() { for (const f of this.subs) { try { f(); } catch (e) { console.error(e); } } },
  queue(key, fn) { const p = (this.queues[key] || Promise.resolve()).then(fn, fn); this.queues[key] = p.catch(() => {}); return p; },
  loadLocal() {
    this.reports = new Map(LS.get('relatos', []).map(r => [r.id, r]));
    this.myVotes = LS.get('votos', {});
    this.votes = this.localVoteCounts(this.myVotes);
    const m = LS.get('mod', {}); this.mod = { oculto: m.oculto || {}, verificado: m.verificado || {} };
    this.perfil = Object.assign({ areas: [], meus: [], visto: 0 }, LS.get('perfil', {}));
  },
  localVoteCounts(mine) { const v = {}; for (const [id, x] of Object.entries(mine)) v[id] = { c: +(x === 'c'), p: +(x === 'p'), f: +(x === 'f') }; return v; },
  async init() {
    this.loadLocal();
    if (MODO_DADOS !== 'api') { this.ready = true; this.emit(); return; }
    /* os relatos vêm do servidor; os guardados no aparelho não se misturam com eles */
    this.mode = 'api'; this.reports = new Map();
    try { const eu = await apiGet('/usuarios/eu'); this.papeis = eu && Array.isArray(eu.papeis) ? eu.papeis : []; } catch (e) { this.papeis = []; }
    await this.carregarRelatos();
    this.ready = true; this.emit();
    setInterval(() => this.carregarRelatos(), CONFIG.atualizarRelatosSeg * 1e3);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') this.carregarRelatos(); });
  },
  /* relatos da janela e, fora dela, os que este aparelho enviou; se falhar, fica com o que já tinha */
  carregarRelatos() {
    return this.queue('relatos', async () => {
      const antes = new Set(this.perfil.meus);
      try {
        const { relatos } = await apiGet('/relatos');
        const m = new Map((relatos || []).map(r => [r.id, r]));
        /* os seus relatos fora da janela: busca cada um só uma vez por sessão */
        const antigos = this.antigos || (this.antigos = new Map());
        const faltam = this.perfil.meus.filter(id => !m.has(id) && !antigos.has(id)).slice(-50);
        const extra = await Promise.all(faltam.map(id => apiGet('/relatos/' + encodeURIComponent(id)).then(x => (x && x.relato) || null, e => { if (e && e.status === 404) return null; throw e; })));
        faltam.forEach((id, i) => antigos.set(id, extra[i]));
        /* o servidor não tem mais (apagado em outra aba ou fora do prazo de retenção): sai de "Meus relatos" e da lista de chaves */
        const sumidos = faltam.filter((id, i) => extra[i] === null);
        if (sumidos.length) {
          const chaves = LS.get('chaves', {});
          for (const id of sumidos) { this.apagados.add(id); delete chaves[id]; }
          LS.set('chaves', chaves);
          this.perfil.meus = this.perfil.meus.filter(id => !this.apagados.has(id)); this.savePerfil();
        }
        for (const id of this.perfil.meus) { const r = antigos.get(id); if (r && !m.has(id)) m.set(id, r); }
        /* relato publicado enquanto a lista carregava; e o apagado nesse meio-tempo não volta */
        for (const id of this.perfil.meus) if (!antes.has(id) && !m.has(id) && this.reports.has(id)) m.set(id, this.reports.get(id));
        for (const id of this.apagados) m.delete(id);
        this.reports = m;
        /* só redesenha se algo mudou (senão a releitura desfaria uma confirmação ou a rolagem do painel) */
        const assinatura = JSON.stringify([...m.values()]);
        if (assinatura !== this.assinatura) { this.assinatura = assinatura; this.emit(); }
      } catch (e) { console.warn('relatos:', e && e.code); }
    });
  },
  async addReport(r) {
    if (this.mode === 'api') {
      const res = await apiPost('/relatos', { tipos: r.tipos, cell: r.cell, quando: r.quando, periodo: r.periodo, texto: r.texto, origem: r.origem });
      const rel = res.relato;
      this.reports.set(rel.id, rel);
      this.perfil.meus = [...this.perfil.meus, rel.id]; this.savePerfil();
      /* lê as chaves de novo e só acrescenta esta: outra aba aberta pode ter gravado as dela */
      const chaves = LS.get('chaves', {}); chaves[rel.id] = res.chave_exclusao; LS.set('chaves', chaves);
      if (LS.get('chaves', {})[rel.id] !== res.chave_exclusao) toast('O relato foi publicado, mas este aparelho não conseguiu guardar a chave para apagá-lo depois.', 8000);
      this.emit(); return rel.id;
    }
    const id = 'l' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    this.reports.set(id, Object.assign({}, r, { id }));
    LS.set('relatos', [...this.reports.values()]);
    this.perfil.meus = [...this.perfil.meus, id]; this.savePerfil(); this.emit(); return id;
  },
  async deleteReport(id) {
    if (this.mode === 'api') {
      const chaves = LS.get('chaves', {}), chave = chaves[id];
      if (!chave) throw new ApiErro('Este aparelho não tem a chave para apagar este relato.', 403, 'forbidden');
      try { await apiDelete('/relatos/' + encodeURIComponent(id), { 'X-Chave-Exclusao': chave }); }
      catch (e) { if (!(e && e.status === 404)) throw e; } // 404: já tinha sido apagado
      this.reports.delete(id); this.apagados.add(id); if (this.antigos) this.antigos.set(id, null);
      const atuais = LS.get('chaves', {}); delete atuais[id]; LS.set('chaves', atuais);
    } else { this.reports.delete(id); LS.set('relatos', [...this.reports.values()]); }
    this.perfil.meus = this.perfil.meus.filter(x => x !== id); this.savePerfil(); this.emit();
  },
  canVote() { return true; },
  async vote(id, v) {
    const mine = Object.assign({}, this.myVotes);
    if (mine[id] === v) delete mine[id]; else mine[id] = v;
    this.myVotes = mine; this.votes = this.localVoteCounts(mine); LS.set('votos', mine); this.emit();
  },
  async setMod(id, key, on) {
    const m = { oculto: Object.assign({}, this.mod.oculto), verificado: Object.assign({}, this.mod.verificado) };
    if (on) m[key][id] = true; else delete m[key][id];
    this.mod = m; LS.set('mod', m); this.emit();
  },
  savePerfil() {
    if (this.mode === 'api') {
      /* outra aba pode ter publicado: junta a lista salva com a desta aba (menos os apagados aqui) antes de gravar */
      const salvos = (LS.get('perfil', {}).meus || []).filter(id => !this.apagados.has(id)), ja = new Set(salvos);
      this.perfil.meus = [...salvos, ...this.perfil.meus.filter(id => !ja.has(id))];
    }
    const p = { areas: this.perfil.areas.slice(0, 40), meus: this.perfil.meus.slice(-200), visto: this.perfil.visto || 0, vistos: (this.perfil.vistos || []).slice(-300) };
    LS.set('perfil', p); return Promise.resolve();
  }
};
