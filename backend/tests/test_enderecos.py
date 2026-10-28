"""O número do imóvel sai; o número da rua e o resto do texto ficam."""
import pytest

from backend.services.enderecos import anonimizar_completo


@pytest.mark.parametrize('entrada, esperado', [
    ('homem armado com capuz cinza roubando na rua 2 cj endereço 1532', 'homem armado com capuz cinza roubando na rua 2 cj [número]'),
    ('moro na Rua das Flores 123 perto', 'moro na Rua das Flores [número] perto'),
    ('av. Brasil, 45 esquina', 'av. Brasil [número] esquina'),
    ('rua 7, 45', 'rua 7 [número]'),
    ('avenida 29 123', 'avenida 29 [número]'),
    ('Endereço: 99 aqui', '[número] aqui'),
    ('casa 12 e nº 5', '[número] e [número]'),
    ('na rua 2 perto da escola', 'na rua 2 perto da escola'),
    ('rua escura com 3 homens', 'rua escura com 3 homens'),
])
def test_numero_do_imovel(entrada, esperado):
    assert anonimizar_completo(entrada).texto == esperado


def test_marca_o_que_removeu_e_e_idempotente():
    r = anonimizar_completo('rua 7, 45 e me liga 19 99876-5432')
    assert r.removidos == ['telefone', 'número de endereço']
    assert anonimizar_completo(r.texto).texto == r.texto
