from sqlalchemy import engine_from_config
from sqlalchemy.orm import configure_mappers
from sqlalchemy.orm import sessionmaker
import zope.sqlalchemy

from . import mymodel
from .mymodel import MyModel

configure_mappers()


def get_engine(settings, prefix='sqlalchemy.'):
    return engine_from_config(settings, prefix)


def get_session_factory(engine):
    factory = sessionmaker()
    factory.configure(bind=engine)
    return factory


def get_tm_session(session_factory, transaction_manager, request=None):
    dbsession = session_factory(info={"request": request})
    zope.sqlalchemy.register(dbsession, transaction_manager=transaction_manager)
    return dbsession


def includeme(config):
    settings = config.get_settings()
    settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'
    config.include('pyramid_tm')
    config.include('pyramid_retry')

    dbengine = settings.get('dbengine')
    if not dbengine:
        dbengine = get_engine(settings)

    session_factory = get_session_factory(dbengine)
    config.registry['dbsession_factory'] = session_factory

    def dbsession(request):
        existing = request.environ.get('app.dbsession')
        if existing is None:
            existing = get_tm_session(session_factory, request.tm, request=request)
        return existing

    config.add_request_method(dbsession, reify=True)
