// Modo atenção do app: com o app fechado, avisa quando surge um alerta perto de onde a pessoa está.
//
// A localização NUNCA vai para o servidor: o app baixa a lista de alertas recentes (GET /api/v1/alertas, sem mandar nada de
// quem pergunta) e compara a posição do aparelho com a de cada alerta aqui mesmo. A cada ~1 minuto o Android entrega uma
// posição para a tarefa abaixo (serviço em primeiro plano, com uma notificação fixa "Modo atenção ligado"), e ela confere a lista.
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as TaskManager from 'expo-task-manager';

export const CHAVE_LINK = 'aurora.link';
const CHAVE_LIGADO = 'aurora.modoAtencao';
const CHAVE_AVISADOS = 'aurora.avisados'; // ids de alertas que já viraram notificação (ou que são do próprio aparelho)
const TAREFA = 'aurora-alertas-proximos';
const RAIO_M = 500; // "perto": até 500 m
const JANELA_H = 6; // só alertas das últimas horas
const INTERVALO_MS = 60_000;

/** Distância em metros entre dois pontos (fórmula de haversine). */
export function distanciaM(lat1, lng1, lat2, lng2) {
  const rad = g => (g * Math.PI) / 180, dLat = rad(lat2 - lat1), dLng = rad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(a));
}

async function lerAvisados() {
  try { return new Set(JSON.parse((await AsyncStorage.getItem(CHAVE_AVISADOS)) || '[]')); } catch { return new Set(); }
}
async function gravarAvisados(ids) {
  await AsyncStorage.setItem(CHAVE_AVISADOS, JSON.stringify([...ids].slice(-200))).catch(() => {});
}

/** O relato que este aparelho acabou de enviar nunca vira notificação para quem o enviou. */
export async function marcarMeuRelato(id) {
  if (typeof id !== 'string' || !/^[0-9a-f]{32}$/.test(id)) return;
  const ids = await lerAvisados();
  ids.add(id);
  await gravarAvisados(ids);
}

/** Confere os alertas recentes contra a posição e avisa dos que estão perto e ainda não foram avisados. Devolve quantos avisou. */
export async function checarAlertas({ latitude, longitude }) {
  const link = await AsyncStorage.getItem(CHAVE_LINK);
  if (!link) return 0;
  const r = await fetch(`${link}api/v1/alertas?janela_horas=${JANELA_H}`, { headers: { Accept: 'application/json' } });
  if (!r.ok) return 0;
  const { alertas } = await r.json();
  const avisados = await lerAvisados();
  let novos = 0;
  for (const a of Array.isArray(alertas) ? alertas : []) {
    if (avisados.has(a.id)) continue;
    const d = distanciaM(latitude, longitude, a.lat, a.lng);
    if (!(d <= RAIO_M)) continue;
    await Notifications.scheduleNotificationAsync({
      content: { title: a.titulo, body: `${a.area} · a cerca de ${Math.max(50, Math.round(d / 50) * 50)} m de você`, sound: 'default',
        data: { cell: a.cell, relato: a.id } },
      trigger: { channelId: 'alertas' }, // na hora, no canal criado em App.js (prioridade alta no Android)
    });
    avisados.add(a.id);
    novos++;
  }
  if (novos) await gravarAvisados(avisados);
  return novos;
}

// A tarefa precisa ser definida quando o app carrega (também quando o Android a acorda com o app fechado).
TaskManager.defineTask(TAREFA, async ({ data, error }) => {
  if (error || !data || !Array.isArray(data.locations) || !data.locations.length) return;
  const { latitude, longitude } = data.locations[data.locations.length - 1].coords;
  try { await checarAlertas({ latitude, longitude }); } catch { /* sem rede ou servidor fora do ar: tenta na próxima posição */ }
});

export async function modoAtencaoLigado() {
  try {
    return (await AsyncStorage.getItem(CHAVE_LIGADO)) === '1' && (await Location.hasStartedLocationUpdatesAsync(TAREFA));
  } catch { return false; }
}

async function iniciarTarefa() {
  await Location.startLocationUpdatesAsync(TAREFA, {
    accuracy: Location.Accuracy.Balanced,
    timeInterval: INTERVALO_MS,
    distanceInterval: 0, // também confere com a pessoa parada: o alerta pode surgir onde ela está
    foregroundService: {
      notificationTitle: 'Aurora · Modo atenção ligado',
      notificationBody: 'Avisando se surgir um alerta perto de você. Sua localização fica só neste aparelho.',
      notificationColor: '#6B4A96',
    },
  });
}

/**
 * Liga o Modo atenção (pede as permissões que faltam). Devolve { ok, ligado, motivo }, com motivo em
 * 'sem-permissao' (localização), 'sem-permissao-fundo' (falta "Permitir o tempo todo"), 'sem-notificacao' ou 'erro'.
 */
export async function ligarModoAtencao() {
  try {
    const fg = await Location.requestForegroundPermissionsAsync();
    if (fg.status !== 'granted') return { ok: false, ligado: false, motivo: 'sem-permissao' };
    const bg = await Location.requestBackgroundPermissionsAsync(); // no Android 11+ abre a tela "Permitir o tempo todo"
    if (bg.status !== 'granted') return { ok: false, ligado: false, motivo: 'sem-permissao-fundo' };
    let nt = await Notifications.getPermissionsAsync();
    if (nt.status !== 'granted') nt = await Notifications.requestPermissionsAsync();
    if (nt.status !== 'granted') return { ok: false, ligado: false, motivo: 'sem-notificacao' };
    await iniciarTarefa();
    await AsyncStorage.setItem(CHAVE_LIGADO, '1');
    return { ok: true, ligado: true };
  } catch (e) {
    return { ok: false, ligado: false, motivo: 'erro' };
  }
}

export async function desligarModoAtencao() {
  try {
    if (await Location.hasStartedLocationUpdatesAsync(TAREFA)) await Location.stopLocationUpdatesAsync(TAREFA);
  } catch { /* já estava parado */ }
  await AsyncStorage.removeItem(CHAVE_LIGADO).catch(() => {});
  return { ok: true, ligado: false };
}

/** Ao abrir o app: se o Modo atenção estava ligado e o Android parou o serviço (reinício do celular, por exemplo), liga de novo sem perguntar nada. */
export async function retomarModoAtencao() {
  try {
    if ((await AsyncStorage.getItem(CHAVE_LIGADO)) !== '1') return false;
    if (await Location.hasStartedLocationUpdatesAsync(TAREFA)) return true;
    const bg = await Location.getBackgroundPermissionsAsync();
    if (bg.status !== 'granted') { await AsyncStorage.removeItem(CHAVE_LIGADO); return false; }
    await iniciarTarefa();
    return true;
  } catch { return false; }
}
