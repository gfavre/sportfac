# -*- coding: utf-8 -*-
from django.conf import settings

MASTER_DB = 'master_users'
LOCAL_DB = 'default'


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class MasterRouter(object):
    def db_for_read(self, model, **hints):
        """
        Reads go to a randomly-chosen replica.
        """
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Writes always go to primary.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        All non-auth models end up in this pool.
        """
        return db != MASTER_DB
