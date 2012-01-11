from tipprapi.tipprapi import TipprAPIClient
from googleoffers.client import GoogleOffers
import logging

################
#Configuration:
import logging.config

LOGGING = {
        'version': 1.0,
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler'
            }
        },                                                                                                                     
        'loggers': {
            'googleoffers-sync': {
                'handlers': ['console'],
                'level'   : 'DEBUG'
                },
        }
}

logging.config.dictConfig(LOGGING)
TOKEN_FILE ='metadata/tokens.dat'
SECRETS_FILE = 'metadata/client_secrets.json'

################

logger = logging.getLogger('googleoffers-sync')

from commons.configuration import open_connection
conn = open_connection()
cursor = conn.cursor()

try:
    tippr_client = TipprAPIClient()
    g_client = GoogleOffers('8793954', TOKEN_FILE, SECRETS_FILE)
    promotions = tippr_client.find_promotions()

    for i, promotion in enumerate(promotions):
        if promotion['status'] in ['approved', 'active', 'closed']:
            print g_client.GetOfferStatus(promotion['id'])

            from commons.persistence import insert                                                                                         
            data = {
                    'tippr_offer_id': promotion['id'],
                    'status'        : status,
                    'last_update'   : last_update_date,
                    }
            insert(cursor, 'googleoffers', data.keys(), data)

            if i % 10:
                conn.commit()
except Exception, e:
    logging.error(e)

conn.commit()
cursor.close()
conn.close()
