from app.utils.lucene_tree_parser import parse_tree


def get_items_by_model(model, model_schema, tree, sort, offset, limit, fields):
    query = model.search_query
    fields = fields.split(",")
    if tree is not None:
        filters = parse_tree(model, query, tree)
        query = query.filter(filters)
        print(query)
    if sort != "":
        sorts = sort.split(",")
        sort_list = []
        for sort in sorts:
            sort = sort.strip()
            direction = sort[0:1]
            sort = sort.lstrip("-+")
            column = getattr(model, sort)
            if column is not None:
                if direction == "-":
                    sort_list.append(column.desc())
                else:
                    sort_list.append(column.asc())
        if len(sort_list) > 0:
            query = query.order_by(*sort_list)
    total_count = query.count()
    query = query.offset(offset).limit(limit)
    items = query.all()
    item_schema = model_schema()
    datas = item_schema.dump(items, many=True).data
    if fields[0] != "_default_":
        list = []
        for data in datas:
            item = {}
            for field in fields:
                field = field.strip()
                if field in data:
                    item[field] = data[field]
            list.append(item)
        datas = list
    return datas, total_count


def get_one_item_by_model(model, model_schema, id, fields, options=None):
    if fields is None:
        fields = "_default_"
    query = model.query
    if options is not None:
        query = query.options(*options)
    item = query.get(id)
    fields = fields.split(",")
    item_schema = model_schema()
    data = item_schema.dump(item, many=False).data
    if fields[0] != "_default_":
        data_filtered = {}
        for field in fields:
            field = field.strip()
            if field in data:
                data_filtered[field] = data[field]
        data = data_filtered
    return data