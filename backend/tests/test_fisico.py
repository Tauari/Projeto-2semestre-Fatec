"""A descrição física sai; roupa, acessório e veículo ficam."""
import pytest

from backend.services.enderecos import anonimizar_completo
from backend.services.fisico import tirar_fisico


@pytest.mark.parametrize('entrada, esperado', [
    ('um homem alto e magro de boina verde me seguiu', 'um homem de boina verde me seguiu'),
    ('um cara negro, alto, com tatuagem no braço e camiseta azul gritou', 'um cara com camiseta azul gritou'),
    ('um rapaz loiro de cabelo curto e capuz cinza me encarou', 'um rapaz com capuz cinza me encarou'),
    ('um homem de uns 30 anos de moto preta', 'um homem de moto preta'),
    ('um sujeito careca com mochila vermelha', 'um sujeito com mochila vermelha'),
    ('ele falou alto e o carro branco parou', 'ele falou alto e o carro branco parou'),
    ('homem de boina verde e camiseta azul', 'homem de boina verde e camiseta azul'),
    ('uma mulher branca de boné me olhou', 'uma mulher de boné me olhou'),
])
def test_tira_so_a_descricao_fisica(entrada, esperado):
    assert tirar_fisico(entrada)[0] == esperado


def test_avisa_o_que_tirou_e_e_idempotente():
    r = anonimizar_completo('um homem alto de boina verde na rua 7, 45')
    assert r.texto == 'um homem de boina verde na rua 7 [número]'
    assert r.removidos == ['número de endereço', 'descrição física']
    assert anonimizar_completo(r.texto).texto == r.texto
    assert tirar_fisico('um homem de boina verde') == ('um homem de boina verde', False)
