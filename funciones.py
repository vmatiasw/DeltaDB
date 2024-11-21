import re
from sqlalchemy import inspect
from db.database import Base
from sqlalchemy.orm import Session, DeclarativeBase
from collections import Counter

class Base(DeclarativeBase):
    pass

def get_all_tables(session: Session) -> list:
    '''
    Devuelve una lista con todas las instancias de todas las tablas de la base de datos.
    Se puede pasar directo a capturar_metadata, capturar_str o capturar_metadata_str para capturar toda la db.
    '''
    all_instances = []
    
    for mapper in Base.registry.mappers: # Iterar sobre las clases mapeadas en la metadata de Base
        instances = session.query(mapper.class_).all()
        all_instances.extend(instances)
    
    return all_instances

def capturar_metadata(objetos: list) -> dict:
    '''
    Devuelve un diccionario donde una clave es una tupla (__tablename__, id)
    y su valor es un diccionario con la metadata de la tabla, donde las claves
    son los nombres de las columnas y los valores son sus valores en el objeto.
    
    Obs: Quizas deban hacer commit de la db.
    '''
    validar_entrada_a_capturar(objetos)

    metadata = {}
    for obj in objetos:
        # Inicializa un diccionario vacío para la metadata de la tabla
        metadata[obj.__tablename__, obj.id] = {}

        # Itera sobre las columnas de la tabla
        for column in inspect(obj).mapper.columns:
            # Obtiene el nombre de la columna y su valor en el objeto
            column_name = column.key
            column_value = getattr(obj, column_name)

            # Verifica si la columna es una clave foránea
            if column.foreign_keys:
                # Si es una ForeignKey, maneja de manera especial si es necesario
                metadata[obj.__tablename__, obj.id][f'{column_name} (FK)'] = column_value
            else:
                # Agrega la columna y su valor al diccionario de metadata
                metadata[obj.__tablename__, obj.id][column_name] = column_value

        # TODO: Captura de propiedades híbridas si las hay.
        # PELIGRO: al ejecutar una propiedad híbrida se puede
        # modificar la db

    return metadata

def capturar_str(objetos: list) -> dict:
    '''
    Devuelve un diccionario donde una clave es una tupla (__tablename__, id)
    y su valor es un diccionario con el __str__ del models de la tabla, donde las claves
    son los nombres de las columnas y los valores son sus valores en el objeto.
    
    Obs: Quizas deban hacer commit de la db.
    '''
    validar_entrada_a_capturar(objetos)

    capturas = {}
    for obj in objetos:
        capturas[obj.__tablename__, obj.id] = {}

        captura = __limpiar_y_convertir(str(obj))

        capturas[obj.__tablename__, obj.id] = captura
    
    return capturas

def comparar_capturas(metadata_inicial: dict, metadata_final: dict):
    '''
    Recibe dos diccionarios de capturas y devuelve un diccionario con las
    modificaciones de cada tabla entre ambas capturas y dos listas con las
    tablas eliminadas y creadas. Todas las listas se devuelven ordenadas.

    Return: modificaciones, eliminadas, creadas
    
    Por ejemplo, si recibie:
    metadata_inicial ={
        ('tabla1', id1): {
            'clave1': valor1,
            'clave2': valor2
        },
        ('tabla2', id2): {
            'clave1': valor1,
            'clave2': valor2
        }
    }

    metadata_final ={
        ('tabla1', id1): {
            'clave1': valor1_modificado,
            'clave2': valor2_igual
        },
        ('tabla3', id3): {
            'clave1': valor1,
            'clave2': valor2
        }
    }

    Devolverá:

    {
        ('tabla1', id1): [
            ('clave1', valor_inicial_1, valor_final_1),
        ],
    }
    [('tabla2', id2)]
    [('tabla3', id3)]


    donde ('clave1', valor_inicial_1, valor_final_1) es una tupla que indica que
    la clave1 tenía el valor valor_inicial_1 en la metadata inicial y
    valor_final_1 en la metadata final.
    '''

    modificaciones = {}
    eliminadas = []
    creadas = []

    for clave_tabla, tabla_inicial in metadata_inicial.items():
        tabla_final = metadata_final.get(clave_tabla, None)
        if tabla_final is None :
            eliminadas.append(clave_tabla)
            continue
        
        assert len(tabla_inicial) == len(tabla_final), 'La cantidad de columnas debe ser la misma'
        assert isinstance(clave_tabla, tuple), f'La clave de la tabla debe ser una tupla en vez de {type(clave_tabla)}'
        assert isinstance(clave_tabla[0], str), f'El primer elemento de la clave de la tabla debe ser un string en vez de {type(clave_tabla[0])}'
        assert isinstance(clave_tabla[1], int), f'El segundo elemento de la clave de la tabla debe ser un entero en vez de {type(clave_tabla[1])}'

        # Lista de cambios detectados para esta tabla
        cambios_actuales = []

        for clave, valor_inicial in tabla_inicial.items():
            valor_final = tabla_final.get(clave, None)
            assert valor_final is not None, f'La columna {clave} de la tabla {clave_tabla} no está en la metadata final'

            if valor_inicial != valor_final:
                cambios_actuales.append((clave, valor_inicial, valor_final))

        if cambios_actuales:
            # Guardamos los cambios en el diccionario con la clave (nombre_tabla, id_tabla)
            modificaciones[clave_tabla] = cambios_actuales

    for clave_tabla, tabla_final in metadata_final.items():
        if metadata_inicial.get(clave_tabla, None) is None:
            creadas.append(clave_tabla)
    
    # Ordenamos las listas
    eliminadas.sort()
    creadas.sort()
    for cambios in modificaciones.values():
        cambios.sort()

    return modificaciones, eliminadas, creadas

def __limpiar_y_convertir(cadena: str) -> dict:
    assert isinstance(cadena, str), 'La captura debe ser una cadena'
    assert cadena.startswith('<') and cadena.endswith('>'), 'La captura debe estar entre < y >'
    assert cadena.count('(') == 1 and cadena.count(')') == 1, 'La captura debe tener un solo paréntesis'
    assert cadena.count('ñ@') == 0, 'La cadena no puede contener ñ@'
    assert cadena.count('[') == cadena.count(']'), 'La cantidad de corchetes debe ser par'

    # Encuentra todos los contenidos dentro de los paréntesis
    contenido = re.findall(r'\((.*?)\)', cadena)

    # Convierto a cadena y elimino comillas simples
    contenido = contenido[0].replace("'", "")

    # Cambio las comas por ñ@
    contenido = re.sub(r'\[(.*?)\]', lambda m: '[' + m.group(1).replace(',', 'ñ@') + ']', contenido)
    contenido = contenido.replace('], [', ']ñ@ [')

    # Divide el contenido por comas para obtener pares clave=valor
    pares = contenido.split(', ')

    # Recupero si hay los ñ@ y los reemplazo por comas
    pares = [par.replace('ñ@', ',') for par in pares]

    # Inicializa un diccionario vacío
    diccionario = {}

    for par in pares:
        # Divide cada par por '='
        assert par.count('=') == 1, 'Cada par debe tener un solo signo igual'
        clave, valor = par.split('=')

        # Elimina espacios en blanco y asigna la clave al diccionario
        clave = clave.strip()

        # Limpia el valor y verifica su tipo
        valor = valor.strip()
        # Intentamos primero convertir a número flotante y verificamos si es entero
        try:
            valor_float = float(valor)
            if valor_float.is_integer():
                diccionario[clave] = int(valor_float)  # Convertimos a entero si no tiene parte decimal
            else:
                diccionario[clave] = valor_float  # Dejamos como flotante si tiene decimales
        except ValueError:
            # Verificamos si es un booleano
            if valor == 'True':
                diccionario[clave] = True
            elif valor == 'False':
                diccionario[clave] = False
            else:
                # Asignamos como cadena cualquier otro valor
                diccionario[clave] = valor

    return diccionario

def validar_entrada_a_capturar(objetos: list):
    '''
    Valida que todos los objetos en la lista sean instancias de Base, 
    tengan el atributo __tablename__ y el atributo id.
    
    Lanza una ValueError si alguna de las condiciones no se cumple.
    '''
    if not all(isinstance(obj, Base) for obj in objetos):
        raise ValueError('Todos los objetos deben ser instancias de models')

    if not all(hasattr(obj, '__tablename__') for obj in objetos):
        raise ValueError('Todos los objetos deben tener __tablename__')

    if not all(hasattr(obj, 'id') for obj in objetos):
        raise ValueError('Todos los objetos deben tener id')

def verificar_tuplas(entrada:list, validos:list)->bool:
    '''
    Recibe un array de entrada del estilo [(str, ?), (str, ?, ?), ...]
    y un array de strings validos del estilo ['str', 'str', ...]
    Devuelve True si todas las entrada tienen strings en validos y todos los strings
    en validos estan en entrada.
    '''
    set_entrada = set([tupla[0] for tupla in entrada])
    set_validos = set(validos)
    if not set_entrada == set_validos:
        diferencia = set_entrada - set_validos
        print(f'Error: Las claves {diferencia} no son válidas.')
        return False
    return True

def verificar_cantidad_tuplas(entrada:list, validos:list)->bool:
    """
    Recibe un array de entrada del estilo [(str, ?), (str, ?, ?), ...]
    y un array de strings validos del estilo [('str',cantidad), ('str',cantidad), ...]
    Devuelve True si todas las entrada tienen la cantidad esperada de strings en validos 
    y todos los strings en validos estan en entrada.
    """
    # Contar las ocurrencias de cada clave en entrada
    contador_entrada = Counter(tupla[0] for tupla in entrada)
    set_validos = set(tupla[0] for tupla in validos)

    # Verificar si todas las claves válidas están presentes en entrada
    if not set_validos.issubset(contador_entrada.keys()):
        diferencia = set_validos - set(contador_entrada.keys())
        print(f'Error: Las claves {diferencia} no son válidas.')
        return False
    
    # Verificar si la cantidad de claves en entrada coincide con la cantidad esperada
    for clave, cantidad in validos:
        if contador_entrada[clave] != cantidad:
            print(f'Error: La cantidad de claves {clave} es {contador_entrada[clave]}, se esperaba {cantidad}.')
            return False
            
    return True
    
def ignorar_valores_de_campos_laxos(modificaciones: dict, campos_laxos: dict):
    '''
    Marca con 'ignoradas' los cambios en los campos especificados en 'campos_laxos' de las tablas especificadas en 
    'modificaciones'.
    Ejemplo:
    > modificaciones = {('partidas', 1): [('duracion_turno', 0, 60), ('iniciada', False, True)]}
    > campos_laxos = {'partidas': ['duracion_turno']}
    > ignorar_valores_de_campos_laxos(modificaciones, campos_laxos)
    > modificaciones == {('partidas', 1): [('duracion_turno', 'ignorado'), ('iniciada', False, True)]}
    '''
    for tabla_id, cambios in modificaciones.items():
        tabla_nombre = tabla_id[0]
        if tabla_nombre in campos_laxos:
            for i, cambio in enumerate(cambios):
                for campo in campos_laxos[tabla_nombre]:
                    if cambio[0] == campo:
                        cambios[i] = (cambio[0], 'ignorado')
                        break

def eliminar_tablas_laxas(modificaciones: dict, tablas_laxas: list):
    '''
    Elimina las tablas especificadas en 'tablas_laxas' de 'modificaciones'.
    Ejemplo:
    > modificaciones = {('partidas', 1): [('duracion_turno', 0, 60), ('iniciada', False, True)]}
    > tablas_laxas = ['partidas']
    > eliminar_tablas_laxas(modificaciones, tablas_laxas)
    > modificaciones == {}
    '''
    claves_a_eliminar = [tabla_id for tabla_id in modificaciones if tabla_id[0] in tablas_laxas]
    for tabla_id in claves_a_eliminar:
        modificaciones.pop(tabla_id)
        
#TODO: Agregar en las de especificar que se pueda pasar para cada str un numero de veces que
# se debe repetir (incluyendo 0). Usar from collections import Counter
def verificar_diccionarios(entrada:dict, validos:dict)->bool:
    '''
    Verifica que toda clave (str,?) en entrada tenga el str en validos y que el str en validos
    tenga un str en entrada.
    Ademas verifica que los valores de cada clave sean validos segun el diccionario de validos,
    utilizando verificar_tuplas.
    '''
    set_entrada = set([clave[0] for clave in entrada.keys()])
    set_validos = set(validos.keys())
    if not set_entrada == set_validos:
        diferencia = set_entrada - set_validos
        print(f'Error: Las claves {diferencia} no son válidas.')
        return False
    
    for clave, valor in entrada.items():
        if not verificar_tuplas(valor, validos[clave[0]]):
            print(f'Error: Los valores de la clave {clave} no son validos segun verificar_tuplas()')
            return False
    return True