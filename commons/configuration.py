import logging
import logging.handlers
import os
import ConfigParser
    
CONFIG_FILE = os.path.join(os.getenv("HOME"), '.tippr_googlesync.cfg')

def configure():
    cfg = ConfigParser.ConfigParser()
    cfg.readfp(open(CONFIG_FILE))
    return cfg

def open_connection():
    import psycopg2
    cfg = configure()
    from_conf = lambda k : cfg.get("Database", k)
    data = dict([(k, from_conf(k)) for k in ['host', 'db', 'user', 'password']])
    return psycopg2.connect("host=%(host)s dbname=%(db)s user=%(user)s password=%(password)s" % data)

def configure_smtp():
    cfg = configure()
    smtp = cfg.get("Smtp", "smtp")
    usr = cfg.get("Smtp", "username")
    pwd = cfg.get("Smtp", "password")
    fromEmail = cfg.get("Smtp", "from")
    
    return (smtp, usr, pwd, fromEmail)
