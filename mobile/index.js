import { registerRootComponent } from 'expo';

import './alertas-proximos'; // define a tarefa de fundo do Modo atenção, também quando o Android a acorda com o app fechado
import App from './App';

registerRootComponent(App);
