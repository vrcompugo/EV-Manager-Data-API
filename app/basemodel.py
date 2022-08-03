from decimal import Decimal
from sqlalchemy.inspection import inspect
from app import db


class BaseModel():

    @staticmethod
    def _extract_sublist(list, key):
        if list is None:
            return None
        sublist = []
        for item in list:
            if item.startswith(key + "."):
                sublist.append(item[len(key) + 1:])
        if len(sublist) > 0:
            return sublist
        return None

    def get_dict_attr(self, key):
        value = getattr(self, key)
        if value is None or isinstance(value, list) or isinstance(value, dict) or isinstance(value, bool) or isinstance(value, BaseModel):
            return value
        if isinstance(value, Decimal):
            return float(value)
        return str(value)

    def to_dict(self, whitelist=None, blacklist=None):
        data = {}
        for c in inspect(self).mapper.column_attrs:
            if blacklist is not None:
                if c.key not in blacklist:
                    data[c.key] = self.get_dict_attr(c.key)
            else:
                if whitelist is not None:
                    if c.key in whitelist:
                        data[c.key] = self.get_dict_attr(c.key)
                else:
                    data[c.key] = self.get_dict_attr(c.key)

        for relationship in inspect(self).mapper.relationships:
            if relationship.key in self.__dict__ and (blacklist is None or relationship.key not in blacklist):
                sub_whitelist = self._extract_sublist(whitelist, relationship.key)
                sub_blacklist = self._extract_sublist(blacklist, relationship.key)
                value = getattr(self, relationship.key)
                if value is not None:
                    if isinstance(value, list):
                        data[relationship.key] = []
                        for item in value:
                            data[relationship.key].append(
                                item.to_dict(whitelist=sub_whitelist, blacklist=sub_blacklist))
                    else:
                        data[relationship.key] = value.to_dict()
                else:
                    data[relationship.key] = None

        return data
