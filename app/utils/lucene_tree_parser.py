from sqlalchemy import and_, or_, not_
from luqum.tree import *


def parse_tree(model, query, tree):
    if isinstance(tree, OrOperation):
        list = []
        for leaf in tree.children:
            list.append(parse_tree(model, query, leaf))
        return or_(*list)
    if isinstance(tree, AndOperation) or isinstance(tree, Group):
        list = []
        for leaf in tree.children:
            list.append(parse_tree(model, query, leaf))
        return and_(*list)
    if isinstance(tree, Not):
        list = []
        for leaf in tree.children:
            list.append(parse_tree(model, query, leaf))
        return not_(*list)
    if isinstance(tree, SearchField):
        if isinstance(tree.children[0], Range):
            return and_(getattr(model, tree.name) >= int(str(tree.children[0].low)), getattr(model, tree.name) <= int(str(tree.children[0].high)))
        if str(tree.children[0].value).strip('"') == "ISNULL":
            return getattr(model, tree.name) == None
        if tree.name == "fulltext":
            searchquery = "%" + \
                str(tree.children[0].value) \
                    .strip('"') \
                    .replace("-","%") \
                    .replace(" ","%") \
                    .replace("*","%") \
                + "%"
            return getattr(model, tree.name).ilike(searchquery)
        searchquery = str(tree.children[0].value).strip('"').replace("*","%")
        if searchquery.find("%") >= 0:
            return getattr(model, tree.name).ilike(searchquery)
        else:
            return getattr(model, tree.name) == searchquery
    return None
