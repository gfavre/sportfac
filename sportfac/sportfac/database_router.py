# -*- coding: utf-8 -*-
from django.conf import settings


MASTER_DB = "master_users"
LOCAL_DB = "default"


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class MasterRouter(object):
    route_app_labels = {}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return MASTER_DB
        return LOCAL_DB

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return MASTER_DB
        return LOCAL_DB

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        All non-auth models end up in this pool.
        """
        return db != MASTER_DB
