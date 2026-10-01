/* vocabulário: tipos de situação, faixas de horário e quando aconteceu */
export const TIPOS = [
  { id: 'assedio', label: 'Assédio verbal', kw: /assedi|cantada|mexeu comigo|falou (coisa|besteira|gracinha)|gracinha|obscen|buzin/ },
  { id: 'perseguicao', label: 'Perseguição', long: 'Perseguição / me seguiram', kw: /segui(u|ram|ndo|da)|persegu|atras de mim|me acompanh/ },
  { id: 'abordagem', label: 'Abordagem indesejada', kw: /abord|chegou em mim|puxou conversa|tentou (falar|conversar|pegar)|insist/ },
  { id: 'intimidacao', label: 'Intimidação', long: 'Encarar ou intimidar', kw: /encar|olhando|observ|intimid|me medindo/ },
  { id: 'exposicao', label: 'Exposição sexual', kw: /exposi|mostrou (as partes|o penis|o orgao)|se masturb|nudez|pelado/ },
  { id: 'roubo', label: 'Roubo ou furto', kw: /roub|furt|assalt|levaram|puxaram (meu|minha)/ },
  { id: 'violencia', label: 'Violência física', kw: /agred|bateu|empurr|soco|tapa|violencia fisica|me pegou|agarr/ },
  { id: 'veiculo', label: 'Situação com veículo', kw: /\bcarro\b|\bmoto\b|veiculo|\buber\b|\b99\b|motorista|\bvan\b|caminhao/ },
  { id: 'ambiente', label: 'Rua escura ou deserta', kw: /escur|desert|sem luz|iluminac|apagad|vazi[ao]/ },
  { id: 'outra', label: 'Outra situação', kw: null }
];
export const TIPO = Object.fromEntries(TIPOS.map(t => [t.id, t]));
export const PERIODOS = [
  { id: 'manha', label: 'Manhã', long: 'Manhã (6h–12h)', from: 6, to: 12 },
  { id: 'tarde', label: 'Tarde', long: 'Tarde (12h–18h)', from: 12, to: 18 },
  { id: '18-20', label: '18–20h', long: '18h–20h', from: 18, to: 20 },
  { id: '20-22', label: '20–22h', long: '20h–22h', from: 20, to: 22 },
  { id: '22-00', label: '22–00h', long: '22h–00h', from: 22, to: 24 },
  { id: 'madrugada', label: 'Madrugada', long: 'Madrugada (0h–6h)', from: 0, to: 6 }
];
export const PER = Object.fromEntries(PERIODOS.map(p => [p.id, p]));
export const QUANDO = { hoje: 'hoje', ontem: 'ontem', semana: 'nesta semana', antes: 'há mais de uma semana' };
export const periodOfHour = hr => (PERIODOS.find(p => hr >= p.from && hr < p.to) || PERIODOS[5]).id;
export const currentPeriod = () => periodOfHour(new Date().getHours());
