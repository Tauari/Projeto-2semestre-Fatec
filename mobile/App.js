// Aurora no celular: abre o app web (o link que a pessoa colou) dentro de um WebView e liga as notificações.
//
// Ponte com a página: antes de a página carregar, o app cria window.AuroraApp = { plataforma, pushToken, areaInicial }.
// A página (frontend/shared/push.js) manda o token e as áreas acompanhadas para o servidor, que avisa quando um relato
// novo cai numa delas. Tocar numa notificação abre a área do alerta (evento "aurora-abrir-area").
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, BackHandler, Linking, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';

const CHAVE_LINK = 'aurora.link';
const CELULA = /^f?-?\d{1,4}_-?\d{1,4}$/;
const ROXO = '#2A2037';
const LILAS = '#B18DE0';

// com o app aberto, o alerta também aparece como banner
Notifications.setNotificationHandler({
  handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }),
});

/** "https://abc.trycloudflare.com/qualquer/coisa" -> "https://abc.trycloudflare.com/"; null se não for um endereço https. */
function normalizarLink(texto) {
  let t = String(texto || '').trim();
  if (!t) return null;
  if (!/^https?:\/\//i.test(t)) t = 'https://' + t;
  const m = t.match(/^(https:\/\/[a-z0-9-]+(?:\.[a-z0-9-]+)+(?::\d{1,5})?)(\/.*)?$/i);
  return m ? m[1] + '/' : null;
}

/** Pede permissão e devolve o token do Expo Push, ou lança um erro com o motivo. */
async function registrarPush() {
  if (!Device.isDevice) throw new Error('Notificações não funcionam em emulador.');
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('alertas', {
      name: 'Alertas da Aurora',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: LILAS,
    });
  }
  let { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') ({ status } = await Notifications.requestPermissionsAsync());
  if (status !== 'granted') throw new Error('A permissão de notificação foi negada.');
  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  if (!projectId) throw new Error('Falta o projectId do EAS (rode "eas init" em mobile/).');
  return (await Notifications.getExpoPushTokenAsync({ projectId })).data;
}

function Tela({ children }) {
  return <View style={estilo.tela}>{children}</View>;
}

function TelaLink({ inicial, aviso, onSalvar, onCancelar }) {
  const [texto, setTexto] = useState(inicial || '');
  const link = normalizarLink(texto);
  return (
    <Tela>
      <Text style={estilo.titulo}>Aurora</Text>
      <Text style={estilo.texto}>Cole o link do Aurora que a equipe te passou (ex.: https://nome.trycloudflare.com).</Text>
      <TextInput
        style={estilo.campo}
        value={texto}
        onChangeText={setTexto}
        placeholder="https://..."
        placeholderTextColor="#857B94"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        returnKeyType="go"
        onSubmitEditing={() => link && onSalvar(link)}
      />
      {texto.trim() && !link ? <Text style={estilo.erro}>Esse endereço não parece um link https válido.</Text> : null}
      <Pressable style={[estilo.botao, !link && estilo.botaoOff]} disabled={!link} onPress={() => onSalvar(link)}>
        <Text style={estilo.botaoTexto}>Abrir a Aurora</Text>
      </Pressable>
      {onCancelar ? (
        <Pressable style={estilo.botaoQuieto} onPress={onCancelar}>
          <Text style={estilo.quietoTexto}>Cancelar</Text>
        </Pressable>
      ) : null}
      {aviso ? <Text style={estilo.aviso}>Notificações desligadas: {aviso}</Text> : null}
    </Tela>
  );
}

export default function App() {
  const [link, setLink] = useState(undefined); // undefined: lendo o que foi salvo; null: nenhum link ainda
  const [token, setToken] = useState(null);
  const [area, setArea] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [pronto, setPronto] = useState(false);
  const [editando, setEditando] = useState(false);
  const [falha, setFalha] = useState(null);
  const [tentativa, setTentativa] = useState(0);
  const web = useRef(null);
  const podeVoltar = useRef(false);

  useEffect(() => {
    AsyncStorage.getItem(CHAVE_LINK).then(v => setLink(v || null), () => setLink(null));
  }, []);

  // notificações: token antes de abrir a página (assim ele já vai em window.AuroraApp) e toque numa notificação
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const resp = Notifications.getLastNotificationResponse(); // app aberto tocando numa notificação
        const cel = resp && resp.actionIdentifier === Notifications.DEFAULT_ACTION_IDENTIFIER ? resp.notification.request.content.data?.cell : null;
        if (typeof cel === 'string' && CELULA.test(cel)) setArea(cel);
        if (resp) Notifications.clearLastNotificationResponse();
        const t = await registrarPush();
        if (vivo) setToken(t);
      } catch (e) {
        if (vivo) setAviso(e && e.message ? e.message : 'erro desconhecido');
      } finally {
        if (vivo) setPronto(true);
      }
    })();
    const sub = Notifications.addNotificationResponseReceivedListener(resp => {
      const cel = resp.notification.request.content.data?.cell; // app já aberto: avisa a página
      if (typeof cel === 'string' && CELULA.test(cel) && web.current) {
        web.current.injectJavaScript(`window.dispatchEvent(new CustomEvent('aurora-abrir-area', { detail: { cell: ${JSON.stringify(cel)} } })); true;`);
      }
    });
    return () => { vivo = false; sub.remove(); };
  }, []);

  // botão voltar do Android: volta no histórico da página antes de fechar o app
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (podeVoltar.current && web.current) { web.current.goBack(); return true; }
      return false;
    });
    return () => sub.remove();
  }, []);

  const salvar = useCallback(async novo => {
    await AsyncStorage.setItem(CHAVE_LINK, novo).catch(() => {});
    setLink(novo); setEditando(false); setFalha(null); setTentativa(n => n + 1);
  }, []);

  // só a página principal conta como falha: um favicon que não existe não derruba o app
  const ehPrincipal = url => !!link && (url === link || url === link.slice(0, -1));

  if (link === undefined || !pronto) {
    return <Tela><ActivityIndicator color={LILAS} size="large" /></Tela>;
  }
  if (!link || editando) {
    return (
      <SafeAreaProvider>
        <StatusBar style="light" />
        <SafeAreaView style={estilo.raiz}>
          <TelaLink inicial={link} aviso={aviso} onSalvar={salvar} onCancelar={link ? () => setEditando(false) : null} />
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }
  if (falha) {
    return (
      <SafeAreaProvider>
        <StatusBar style="light" />
        <SafeAreaView style={estilo.raiz}>
          <Tela>
            <Text style={estilo.titulo}>Não consegui abrir a Aurora</Text>
            <Text style={estilo.texto}>{falha}</Text>
            <Pressable style={estilo.botao} onPress={() => { setFalha(null); setTentativa(n => n + 1); }}>
              <Text style={estilo.botaoTexto}>Tentar de novo</Text>
            </Pressable>
            <Pressable style={estilo.botaoQuieto} onPress={() => setEditando(true)}>
              <Text style={estilo.quietoTexto}>Trocar o link</Text>
            </Pressable>
            {aviso ? <Text style={estilo.aviso}>Notificações desligadas: {aviso}</Text> : null}
          </Tela>
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  const antes = `window.AuroraApp = ${JSON.stringify({ plataforma: 'expo', pushToken: token, areaInicial: area })}; true;`;
  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <SafeAreaView style={estilo.raiz}>
        <WebView
          key={tentativa}
          ref={web}
          source={{ uri: link }}
          injectedJavaScriptBeforeContentLoaded={antes}
          javaScriptEnabled
          domStorageEnabled
          setSupportMultipleWindows={false}
          allowsBackForwardNavigationGestures
          startInLoadingState
          renderLoading={() => <Tela><ActivityIndicator color={LILAS} size="large" /></Tela>}
          onNavigationStateChange={s => { podeVoltar.current = s.canGoBack; }}
          onShouldStartLoadWithRequest={req => {
            // tudo do próprio Aurora abre aqui; telefone, e-mail e sites de fora abrem no app do aparelho
            if (req.url.startsWith(link) || req.url === 'about:blank') return true;
            if (/^(tel:|mailto:|https?:\/\/)/i.test(req.url)) Linking.openURL(req.url).catch(() => {});
            return false;
          }}
          onError={e => { if (ehPrincipal(e.nativeEvent.url)) setFalha('Sem conexão ou o endereço está errado.'); }}
          onHttpError={e => {
            const { url, statusCode } = e.nativeEvent;
            if (ehPrincipal(url) && statusCode >= 500) setFalha('O servidor da Aurora está fora do ar (código ' + statusCode + '). O link pode ter mudado: peça o novo para a equipe.');
          }}
        />
        <Pressable style={estilo.engrenagem} accessibilityLabel="Trocar o link da Aurora" onPress={() => setEditando(true)}>
          <Text style={estilo.engrenagemTexto}>⚙</Text>
        </Pressable>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const estilo = StyleSheet.create({
  raiz: { flex: 1, backgroundColor: ROXO },
  tela: { flex: 1, backgroundColor: ROXO, alignItems: 'stretch', justifyContent: 'center', padding: 24, gap: 14 },
  titulo: { color: '#F1EBF7', fontSize: 26, fontWeight: '700', textAlign: 'center' },
  texto: { color: '#C5BAD3', fontSize: 16, lineHeight: 22, textAlign: 'center' },
  campo: { backgroundColor: '#352B43', color: '#F1EBF7', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 16, borderWidth: 1, borderColor: '#463955' },
  erro: { color: '#EB7FA2', fontSize: 14, textAlign: 'center' },
  botao: { backgroundColor: LILAS, borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  botaoOff: { opacity: 0.4 },
  botaoTexto: { color: '#1A1322', fontSize: 16, fontWeight: '700' },
  botaoQuieto: { paddingVertical: 12, alignItems: 'center' },
  quietoTexto: { color: '#C5BAD3', fontSize: 15 },
  aviso: { color: '#978BA8', fontSize: 13, textAlign: 'center', marginTop: 8 },
  engrenagem: { position: 'absolute', left: 6, bottom: 6, width: 30, height: 30, borderRadius: 15, backgroundColor: ROXO, alignItems: 'center', justifyContent: 'center', opacity: 0.35 },
  engrenagemTexto: { color: '#F1EBF7', fontSize: 16 },
});
