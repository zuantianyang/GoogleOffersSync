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
                'level'   : 'INFO'
                },
            'tippr-api': {
                'handlers': ['console'],
                'level'   : 'ERROR'
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
from commons.persistence import dinsert, register_named_entity

logger = logging.getLogger('googleoffers-sync')
today = date.today()


def register_promotion(conn, cursor, promotion):
    promotion_id = promotion['id']
    cursor.execute('select * from promotions where id = %s', [promotion_id])
    if not cursor.fetchone():
        offer = promotion['offer']
        category = offer['category']
        category_id = register_named_entity(conn, cursor, category, 'categories', dict(label=category['label']))
        advertiser_id = register_named_entity(conn, cursor, offer['advertiser'], 'advertisers')
        data = {
                'id'                : promotion_id,
                'marketplace_status': promotion['status'],
                'name'              : promotion['name'].encode('utf-8'),
                'start_date'        : promotion['start_date'],
                'end_date'          : promotion['end_date'],
                'category_id'       : category_id,
                'advertiser_id'     : advertiser_id
                }
        dinsert(cursor, 'promotions', data)
        sites = promotion.get('publisher', {}).get('sites', [])
        for site in sites:
            market_id = register_named_entity(conn, cursor, site['market'], 'markets')
            dinsert(cursor, 'promotion_market', dict(promotion_id=promotion_id, market_id=market_id))
        conn.commit()

def register_promotion_history(conn, cursor, promotion, g_status):
    data = {
            'promotion_id': promotion['id'],
            'status'      : g_status,
            'last_update' : datetime.datetime.now()
            }
    dinsert(cursor, 'promotion_status_history', data)
    conn.commit()

def update_redemption_data(conn, cursor, g_client, pid):
    for status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
        redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, status)
        size = len(redemption_codes.get('offer', {}).get('codes', []))
                    
        logger.debug("%s / %s / %s" % (pid, status, size))
        data = {
                'promotion_id': pid,
                'size'        : size,
                'status'      : status,
                'last_update' : datetime.datetime.now()
                }
        dinsert(cursor, 'redemption_codes', data)
    conn.commit()

def expire_promotion(tippr_client, g_client, promotion):
    pid = promotion['id']
    end_date = datetime.datetime.strptime(promotion['end_date'], "%Y-%m-%d").date()
    if end_date < today:
        for status in ['CREATED', 'REFUNDED', 'CANCELLED']:
            try:
                redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, status)
                vouchers = tippr_client.find_vouchers(pid)
                for r in redemption_codes.get('offer', {}).get('codes', []):         
                    for i, voucher in enumerate(vouchers):
                        logger.info("Processing PromotionID: %s - Voucher: %s - Redemption Code: %s" % (pid, voucher['id'], voucher['redemption_code']))
                        if voucher['status'] != 'returned' and voucher['voucher_code'] == r['id']:
                            logger.debug("PromotionID: %s - Voucher: %s - Redemption Code: %s - Returned succesfully!" % (pid, voucher, r['id']))
                            tippr_client.return_voucher(voucher['id'])
            except Exception, e:
                logging.exception(e)
                continue
                
        #tippr_client.close_promotion(pid)

def sync(tippr_client, g_client):
    conn = open_connection()
    cursor = conn.cursor()
    try:
        promotions = tippr_client.find_promotions()

        for i, promotion in enumerate(promotions):
            pid = promotion['id']
            promotion_status = promotion['status']
            end_date = datetime.datetime.strptime(promotion['end_date'], "%Y-%m-%d").date()
                    
            logger.info('processing promotion id: %s, status is %s' % (pid, promotion_status))
            register_promotion(conn, cursor, promotion)
            try:
                if promotion_status in ['approved', 'active', 'closed']:
                    g_status = g_client.GetOfferStatus(pid)
                    register_promotion_history(conn, cursor, promotion, g_status)
                    update_redemption_data(conn, cursor, g_client, pid)
                #elif promotion_status == 'expired':
                if end_date < today and promotion_status: #not in ['finalized','rejected', 'draft', 'submitted', 'closed']:
                    expire_promotion(tippr_client, g_client, promotion)
            except GoogleOffersError:
                logging.exception("Error in google offers")
    except Exception, e:
        logging.exception("Error in google offers sync")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("*** END ***")

def main():
    tippr_client = TipprAPIClient()
    g_client = GoogleOffers('8793954', TOKEN_FILE, SECRETS_FILE)
    sync(tippr_client, g_client)

if __name__ == "__main__":
    main()