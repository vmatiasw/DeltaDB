import os
import django
from django.db import models, transaction
from django.conf import settings
from django.core.management import call_command
from django.apps import AppConfig

from DeltaDB.DBConnection.DBConnectionAdapter import DBConnectionAdapter
from DeltaDB.config import APP_LABEL

class TestAppConfig(AppConfig):
    name = APP_LABEL
    path = os.path.dirname(os.path.abspath(__file__))
    def __init__(self):
        super().__init__(app_name=self.name, app_module=self.path)

class DjangoDBConnectionAdapter(DBConnectionAdapter):
    def __init__(self, app_label:str)->None:
        super().__init__()
        self.app_label = app_label
        self._setup_django()
        
    def _get_engine(self) -> str:
        """Devuelve el motor de la base de datos."""
        engines = {
            'sqlite': 'sqlite3',
            'mysql': 'mysql',
            'postgresql': 'postgresql',
        }
        try:
            return engines[self.database]
        except KeyError:
            raise Exception(f"Database {self.database} not supported")
        
    def _setup_base(self):
        """Configura la clase Base de Django."""
        class Base(models.Model):
            pass
        self.base = Base
    
    def _setup_django(self):
        """Configura el entorno de Django para la base de datos seleccionada."""
        settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': f'django.db.backends.{self._get_engine()}',
                    'NAME': self.db_name,
                    'USER': self.username,
                    'PASSWORD': self.password,
                    'HOST': self.host,
                    'PORT': self.port,
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                f'{self.app_label}.apps.TestAppConfig',
            ]
        )
        django.setup()
        TestAppConfig().ready()

    def get_base(self):
        """Devuelve la clase Base de Django (en este caso, no hay Base explícita como en SQLAlchemy)."""
        return self.base

    def get_new_session(self):
        """
        Devuelve una sesión nueva de Django, pero en realidad, Django maneja la transacción automáticamente.
        Si se necesita un control manual, se puede usar el contexto de transacciones.
        """
        return transaction.atomic()

    def create_tables(self) -> None:
        """Crea las tablas en la base de datos utilizando Django ORM."""
        call_command('migrate')

    def drop_tables(self) -> None:
        """Elimina las tablas en la base de datos utilizando Django ORM."""
        call_command('flush', '--no-input')