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
from datetime import timedelta
from tipprapi.tipprapi import TipprAPIClient
from googleoffers.client import GoogleOffers, GoogleOffersError
from commons.configuration import open_connection
from commons.persistence import dinsert, register_named_entity

logger = logging.getLogger('googleoffers-sync')
today = date.today()
yesterday = today - timedelta(days=1)

def get_code_type(code, vouchers):
    """ Find out if this is a voucher_code or redemption_code """
    for v in vouchers:
        if code in v['voucher_code']:
            return 'voucher_code'
        elif v['redemption_code']:
            return 'redemption_code'
    logger.info("Unable to find voucher code %s\n" % code['id'])
        
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
                'headline'          : promotion['offer']['headline'].encode('utf-8'),
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
    pid = promotion['id']
    data = {
            'promotion_id':pid,
            'status'      : g_status,
            'last'        : True,
            'last_update' : datetime.datetime.now()
            }
    cursor.execute('update redemption_codes set last=false where promotion_id = %s', [pid])
    dinsert(cursor, 'promotion_status_history', data)
    conn.commit()

def update_redemption_data(conn, cursor, g_client, pid):
    for status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
        try:
            redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, status)
            size = len(redemption_codes.get('offer', {}).get('codes', []))
                        
            logger.debug("%s / %s / %s" % (pid, status, size))
            data = {
                    'promotion_id': pid,
                    'size'        : size,
                    'status'      : status,
                    'last'        : True,
                    'last_update' : datetime.datetime.now()
                    }
            cursor.execute('update redemption_codes set last=false where promotion_id = %s and status=%s', [pid, status])
            dinsert(cursor, 'redemption_codes', data)
        except:
            continue
    conn.commit()

def process_expired_promotion(tippr_client, g_client, promotion):
    pid = promotion['id']
    
    #retrieve all offer's vouchers from TOM
    vouchers = tippr_client.find_vouchers(pid)
    v = []
    for i, voucher in enumerate(vouchers):
        v.append(voucher)
    
    purchased_codes = []
    try:
        codes = g_client.GetRedemptionCodesWithStatus(pid, 'PURCHASED')
        purchased_codes = [c['id'] for c in codes.get('offer').get('codes', [])]
    except:
        pass    

    if purchased_codes:
        code_type = get_code_type(purchased_codes[0], v)
    else:
        code_type = 'voucher_code'
    
    for vv in v:
        if vv[code_type] not in purchased_codes:
            print "returning voucher... " + str(vv['id']) + " / " + str(vv[code_type])
            tippr_client.return_voucher(vv['id'])

    logger.info("Closing Promotion ID %s" % str(pid))
    response = tippr_client.close_promotion(pid)
    logger.info("Promotion ID %s closed. Response is: %s" % (str(pid), str(response)))
    
    

def sync(tippr_client, g_client):
    conn = open_connection()
    cursor = conn.cursor()
    
    try:
        promotions = tippr_client.find_promotions()
        
        for promotion in promotions:
            pid = promotion['id']
                        
            
            promotion_status = promotion['status']
            end_date = datetime.datetime.strptime(promotion['end_date'], "%Y-%m-%d").date()
                    
            logger.info('processing promotion id: %s, %s, status is %s, expires on %s ' % (pid, promotion['name'], promotion_status, end_date))
            register_promotion(conn, cursor, promotion)
            try:
                if promotion_status in ['approved', 'active', 'closed']:
                    g_status = g_client.GetOfferStatus(pid)
                    register_promotion_history(conn, cursor, promotion, g_status)
                    update_redemption_data(conn, cursor, g_client, pid)
                    
                    if end_date < today and end_date >= yesterday:
                        #process_expired_promotion(tippr_client, g_client, promotion)
                        pass
                    
            except GoogleOffersError, e:
                logging.exception("Error in google offers" + str(e))
    except Exception, e:
        logging.exception("Error in google offers sync" + str(e))

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