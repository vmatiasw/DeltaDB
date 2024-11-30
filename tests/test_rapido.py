import DeltaDB.data_processing.analysis as comp
import DeltaDB.data_processing.ingestion as ing

from tests.db.GameFactory import GameFactory

def test_iniciar_partida(test_session):
    '''Test para iniciar una partida con suficientes jugadores'''
    game = GameFactory(test_session)
    
    partida = test_session.get('Partida', 1)
    
    captura_inicial = ing.capture_all_tables(test_session)
    
    assert captura_inicial == {('jugadores', 1): {'id': 1, 'nombre': 'Creador', 'es_creador': True, 'id_partida (FK)': 1, 'orden': 0}, ('jugadores', 2): {'id': 2, 'nombre': 'Jugador2', 'es_creador': False, 'id_partida (FK)': 1, 'orden': 1}, ('jugadores', 3): {'id': 3, 'nombre': 'Jugador3', 'es_creador': False, 'id_partida (FK)': 1, 'orden': 2}, ('jugadores', 4): {'id': 4, 'nombre': 'Creador', 'es_creador': True, 'id_partida (FK)': 2, 'orden': 0}, ('jugadores', 5): {'id': 5, 'nombre': 'Jugador2', 'es_creador': False, 'id_partida (FK)': 2, 'orden': 1}, ('jugadores', 6): {'id': 6, 'nombre': 'Jugador3', 'es_creador': False, 'id_partida (FK)': 2, 'orden': 2}, ('partidas', 1): {'id': 1, 'nombre_partida': 'Partida', 'nombre_creador': 'Creador', 'iniciada': False, 'inicio_turno': '0', 'duracion_turno': 0, 'tablero': '[[2, 1, 3, 4, 2, 3], [4, 2, 1, 1, 3, 3], [2, 1, 3, 2, 3, 4], [4, 1, 1, 2, 2, 4], [1, 3, 1, 2, 1, 3], [2, 3, 4, 4, 4, 4]]'}, ('partidas', 2): {'id': 2, 'nombre_partida': 'Partida', 'nombre_creador': 'Creador', 'iniciada': False, 'inicio_turno': '0', 'duracion_turno': 0, 'tablero': '[[2, 1, 3, 4, 2, 3], [4, 2, 1, 1, 3, 3], [2, 1, 3, 2, 3, 4], [4, 1, 1, 2, 2, 4], [1, 3, 1, 2, 1, 3], [2, 3, 4, 4, 4, 4]]'}}
    
    game.iniciar_partida(partida)
    
    captura_final = ing.capture_all_tables(test_session)

    assert captura_final != captura_inicial
    
    captura_inicial[('jugadores', 1)].pop('es_creador')
    captura_final[('jugadores', 1)].pop('nombre')
    
    changes, created, deleted = comp.diff_captures(captura_inicial, captura_final)

    assert created.get_frequency() == {'cartas': 6}
    assert not deleted.get_frequency()
    assert changes.get_frequency() == {'partidas': {'#table frequency': 1, 'iniciada': 1, 'inicio_turno': 1, 'duracion_turno': 1}, 'jugadores': {'#table frequency': 1, 'es_creador': 1, 'nombre': 1}}
    assert created.data == {('cartas', 5), ('cartas', 4), ('cartas', 1), ('cartas', 3), ('cartas', 6), ('cartas', 2)}
    assert not deleted.data
    assert changes.data == {('partidas', 1): {'iniciada': (False, True), 'inicio_turno': ('0', '2021-10-10T10:00:00Z'), 'duracion_turno': (0, 60)}, ('jugadores', 1): {'es_creador': ("#column don't exist", True), 'nombre': ('Creador', "#column don't exist")}}
    assert created.remove_tables(['jugadores']).data == {('cartas', 1), ('cartas', 2), ('cartas', 3), ('cartas', 4), ('cartas', 5), ('cartas', 6)}
    assert not deleted.remove_tables(['jugadores']).data
    assert changes.ignore_diff_fields({'partidas': ['iniciada']}).remove_tables(['jugadores']).data == {('partidas', 1): {'duracion_turno': (0, 60), 'iniciada': ('#change ignored', '#change ignored'), 'inicio_turno': ('0', '2021-10-10T10:00:00Z')}}
    assert changes.ignore_diff_fields({'partidas': ['iniciada']}).data == {('partidas', 1): {'iniciada': ('#change ignored', '#change ignored'), 'inicio_turno': ('0', '2021-10-10T10:00:00Z'), 'duracion_turno': (0, 60)}}
    assert created.matches_schema({'cartas'})
    assert deleted.matches_schema(set())
    assert changes.matches_schema({('partidas', 1): {'iniciada', 'inicio_turno', 'duracion_turno'}})

