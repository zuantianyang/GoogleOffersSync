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

