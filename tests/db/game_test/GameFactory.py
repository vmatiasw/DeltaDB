from typing import Any

MOCK_GMT_TIME_ZT = "2021-10-10T10:00:00Z"
SEGUNDOS_TEMPORIZADOR_TURNO = 60
N_CARTAS_FIGURA_TOTALES = 6


class GameFactory:

    def __init__(self, repository: Any):
        self.repository = repository

    def crear_partida(self) -> Any:
        """Crea una partida inicial con un creador y la agrega a la base de datos."""
        partida = self.repository.instance_model(
            "Partida",
            nombre_partida="Partida",
            nombre_creador="Creador",
            iniciada=False,
        )
        partida_id = self.repository.get_key(partida)
        creador = self.repository.instance_model(
            "Jugador", nombre="Creador", partida_id=partida_id, es_creador=True, orden=0
        )
        self.repository.append(partida.jugadores, creador)

        self.repository.add(creador)
        self.repository.add(partida)
        self.repository.flush()
        return partida

    def unir_jugadores(self, partida: Any, numero_de_jugadores: int = 1) -> list[Any]:
        """Agrega jugadores a una partida existente."""
        assert partida.iniciada == False, "La partida ya ha sido iniciada"

        assert (
            numero_de_jugadores < 4
        ), "No se pueden unir más de 4 jugadores a la partida"

        if numero_de_jugadores == 0:
            return []

        nuevos_jugadores = []
        for i in range(numero_de_jugadores):
            partida_id = self.repository.get_key(partida)
            nuevo_jugador = self.repository.instance_model(
                "Jugador",
                nombre=f"Jugador{i+2}",
                partida_id=partida_id,
                es_creador=False,
                orden=self.repository.count(partida.jugadores),
            )

            self.repository.add(nuevo_jugador)
            self.repository.append(partida.jugadores, nuevo_jugador)
            nuevos_jugadores.append(nuevo_jugador)
            self.repository.flush()

        self.repository.flush()
        return nuevos_jugadores

    def iniciar_partida(self, partida: Any) -> Any:
        """Inicia una partida, reparte cartas y actualiza el estado de la partida."""
        assert partida.iniciada == False, "La partida ya ha sido iniciada"

        partida.iniciada = True
        partida.inicio_turno = MOCK_GMT_TIME_ZT
        partida.duracion_turno = SEGUNDOS_TEMPORIZADOR_TURNO

        self.__repartir_cartas(partida, 3, 2)

        self.repository.flush([partida])
        return partida

    def __repartir_cartas(
        self, partida: Any, n_cartas_reveladas: int, n_cartas_por_jugador: int
    ):
        """Reparte las cartas entre los jugadores de una partida."""
        assert partida.iniciada == True, "La partida no ha sido iniciada"

        jugadores = self.repository.get_list(partida.jugadores)
        # Crear las cartas de figura
        for jugador in jugadores:
            for i in range(
                n_cartas_por_jugador - self.repository.count(jugador.mazo_cartas)
            ):
                jugador_id = self.repository.get_key(jugador)
                carta = self.repository.instance_model(
                    "Carta", jugador_id=jugador_id, revelada=(i < n_cartas_reveladas)
                )

                self.repository.add(carta)
                self.repository.append(jugador.mazo_cartas, carta)

        self.repository.flush()
