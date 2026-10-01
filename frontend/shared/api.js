/* acesso à API do servidor da Aurora (/api/v1) */
import { CONFIG } from '../config.js';

export class ApiErro extends Error {
  constructor(message, status = 0, code = 'server') { super(message); this.name = 'ApiErro'; this.status = status; this.code = code; }
}
const CODIGOS = { 403: 'forbidden', 404: 'not_found', 422: 'invalid_argument', 429: 'rate_limited' };
async function pedir(method, path, body, headers) {
  const opt = { method, headers: Object.assign({ Accept: 'application/json' }, headers) };
  if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
  let res;
  try { res = await fetch(CONFIG.apiBase + path, opt); } catch (e) { throw new ApiErro('Sem conexão com o servidor.', 0, 'network'); }
  if (res.status >= 400) {
    let detail = '';
    try { const j = await res.json(); if (j && typeof j.detail === 'string') detail = j.detail; } catch (e) { /* corpo sem JSON */ }
    throw new ApiErro(detail || 'O servidor respondeu com erro ' + res.status + '.', res.status, CODIGOS[res.status] || 'server');
  }
  if (res.status === 204) return null;
  try { return await res.json(); } catch (e) { throw new ApiErro('Resposta do servidor em formato inesperado.', res.status, 'server'); }
}
export const apiGet = path => pedir('GET', path);
export const apiPost = (path, body) => pedir('POST', path, body);
export const apiDelete = (path, headers) => pedir('DELETE', path, undefined, headers);
