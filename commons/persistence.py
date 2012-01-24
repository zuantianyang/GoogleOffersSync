#entity registration:

def register_entity(conn, cursor, entity, table, fields={}):
    entity_id = entity['id']
    cursor.execute('select * from ' + table + ' where id = %s', [entity_id])
    if not cursor.fetchone():
        data = dict(id=entity_id)
        data.update(fields)
        dinsert(cursor, table, data)
    return entity_id 

def register_named_entity(conn, cursor, entity, table, fields={}):
    fields['name'] = entity['name'].encode('utf-8')
    return register_entity(conn, cursor, entity, table, fields)

#low level utils for sql interaction:

def insert(cursor, table, fields, data, returns=None):
    sql = "insert into " + table + "(" + ", ".join(fields) + ") " + \
            "values(" + ", ".join(["%s"] * len(fields)) + ")"
    if returns:
        sql += ' returning ' + ",".join(returns)
    cursor.execute(sql, [data[f] for f in fields])

#shortcut: insert from dict
def dinsert(cursor, table, data, returns=None):
    insert(cursor, table, data.keys(), data, returns)

def update(cursor, table, fields, data, where=None):
    sql = "update " + table + " set " + \
            ', '.join([ '%(field)s=%(place)s' % dict(field=f, place="%s") for f in fields])
    params = [data[f] for f in fields]
    if where:
        sql += " " + where[0]
        params += where[1]
    cursor.execute(sql, params)

