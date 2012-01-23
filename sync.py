import logging
import commons.dictconfig

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
            'tippr-api': {
                'handlers': ['console'],
                'level'   : 'DEBUG'
                }
        }
}

commons.dictconfig.dictConfig(LOGGING)

TOKEN_FILE ='metadata/tokens.dat'
SECRETS_FILE = 'metadata/client_secrets.json'

################

import datetime
from datetime import date
from tipprapi.tipprapi import TipprAPIClient
from googleoffers.client import GoogleOffers, GoogleOffersError
from commons.configuration import open_connection
from commons.persistence import insert                                                                                         

logger = logging.getLogger('googleoffers-sync')
today = date.today()

def register_offer(conn, cursor, promotion, g_status):
    data = {
            'promotion_id': promotion['id'],
            'status'        : g_status,
            'last_update'   : datetime.datetime.now()
            }
    insert(cursor, 'promotions', data.keys(), data)

def update_redemption_data(g_client, redemtion_data, pid, g_status):
    for status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
        redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, status)
        size = len(redemption_codes.get('offer', {}).get('codes', []))
        redemtion_data[status] = size
    return redemtion_data

def expire_promotion(tippr_client, g_client, promotion):
    pid = promotion['id']
    end_date = datetime.datetime.strptime(promotion['end_date'], "%Y-%m-%d").date()
    if end_date < today:
        for status in ['CREATED', 'REFUNDED', 'CANCELLED']:
            redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, status)
            vouchers = tippr_client.find_vouchers(pid)
            for r in redemption_codes.get('offer', {}).get('codes', []):         
                for voucher in vouchers:
                    if voucher['status'] != 'returned' and voucher['redemption_code'] == r['id']:
                        logger.debug("PromotionID: %s - Voucher: %s - Redemption Code: %s" % (pid, voucher, r['id']))
                        tippr_client.return_voucher(voucher['id']) 
        tippr_client.close_promotion(pid)

def sync():
    conn = open_connection()
    cursor = conn.cursor()
    try:
        tippr_client = TipprAPIClient()
        g_client = GoogleOffers('8793954', TOKEN_FILE, SECRETS_FILE)
        promotions = tippr_client.find_promotions()

        redemtion_data = dict()
        for i, promotion in enumerate(promotions):
            promotion_status = promotion['status']
            pid = promotion['id']
            logger.debug('processing promotion id: %s, status is %s' % (pid, promotion_status))
            try:
                if promotion_status in ['approved', 'active', 'closed']:
                    g_status = g_client.GetOfferStatus(pid)
                    register_offer(conn, cursor, promotion, g_status)
                    redemtion_data = update_redemption_data(g_client, redemtion_data, pid, g_status)
                    
                    for g_status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
                        logger.debug("%s / %s / %s" % (pid, g_status, str(redemtion_data.get(g_status, 0))))
                        data = {
                                'promotion_id' : pid,
                                'size'       : redemtion_data.get(g_status, 0),
                                'status'     : g_status,
                                'last_update': datetime.datetime.now()
                                }
                        insert(cursor, 'redemption_codes', data.keys(), data)
                    conn.commit()
                    
                elif promotion_status == 'expired':
                    expire_promotion(tippr_client, g_client, promotion)
                if i % 10:
                    conn.commit()
            except GoogleOffersError:
                logging.exception("Error in google offers")


            
    except Exception, e:
        logging.exception("Error in google offers sync")

    conn.commit()
    cursor.close()
    conn.close()
    logger.debug("*** END ***")

if __name__ == "__main__":
    sync()

