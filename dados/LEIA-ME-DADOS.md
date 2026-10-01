# Dados

- `data.json`: dados já agregados que o app usa (células de ~1 km, contagens por bairro, estatísticas da pesquisa). Não tem respostas individuais.
- `rede-de-apoio.json`: endereços, telefones, horários e posições da rede de apoio. Edite aqui e rode `python scripts/montar.py` (versão original). Na nova versão, basta reiniciar o servidor.

Os arquivos brutos (`pesquisa-seguranca-mulheres-rio-claro.csv` e `ocorrencias-rio-claro-completo.md`) ficam fora do repositório de propósito, porque trazem respostas individuais. Para regenerar o `data.json`, coloque esses dois arquivos nesta pasta e rode `python scripts/preparar_dados.py`. O `.gitignore` impede que eles sejam enviados por engano.
