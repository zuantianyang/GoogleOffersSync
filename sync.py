from tipprapi.tipprapi import TipprAPIClient
from googleoffers.client import GoogleOffers, GoogleOffersError
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

from commons.persistence import insert                                                                                         
from datetime import date

def find_status_size(g_client, pid, status):
    codes = g_client.GetRedemptionCodesWithStatus(pid, status)
    return len(codes.get('offer', {}).get('codes', []))

from commons.configuration import open_connection
conn = open_connection()
cursor = conn.cursor()

try:
    tippr_client = TipprAPIClient()
    g_client = GoogleOffers('8793954', TOKEN_FILE, SECRETS_FILE)
    promotions = tippr_client.find_promotions()

    redemtion_data = dict()
    for i, promotion in enumerate(promotions):
        if promotion['status'] in ['approved', 'active', 'closed']:
            try:
                pid = promotion['id']
                status = g_client.GetOfferStatus(pid)
            
                #if status in ['active']: #TODO
                for status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
                    size = find_status_size(g_client, pid, status)
                    redemtion_data[status] = redemtion_data.get(status, 0) + size

                last_update_date = date.today() #TODO
                data = {
                        'tippr_offer_id': promotion['id'],
                        'status'        : status,
                        'last_update'   : last_update_date,
                        }
                insert(cursor, 'google_offers', data.keys(), data)

                if i % 10:
                    conn.commit()
            except GoogleOffersError:
                pass

    last_update_date = date.today()
    for status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
        data = {
                'size'       : redemtion_data[status],
                'status'     : status,
                'last_update': last_update_date,
                }
        insert(cursor, 'redemption_codes', data.keys(), data)
        conn.commit()
except Exception, e:
    logging.exception("Error in google offers sync")

conn.commit()
cursor.close()
conn.close()
