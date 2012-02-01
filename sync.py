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
tomorrow = today + timedelta(days=1)
yesterday = today - timedelta(days=1)


def get_code_type(code, vouchers):
    """ Find out if this is a voucher_code or redemption_code """
    for v in vouchers:
        if code in v['voucher_code']:
            return 'voucher_code'
        elif code in v['redemption_code']:
            return 'redemption_code'
    print "Unable to find voucher code %s\n" % code['id']
        
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
                'last'        : True,
                'last_update' : datetime.datetime.now()
                }
        cursor.execute('update redemption_codes set last=false where promotion_id = %s and status=%s', [pid, status])
        dinsert(cursor, 'redemption_codes', data)
    conn.commit()

def process_expired_promotion(tippr_client, g_client, promotion):
    pid = promotion['id']
    
    #retrieve all offer's vouchers from TOM
    vouchers = tippr_client.find_vouchers(pid)
      
    codes = g_client.GetRedemptionCodesWithStatus(pid, 'PURCHASED')
    purchased_codes = [c['id'] for c in codes.get('offer').get('codes', [])]

    if purchased_codes:
        code_type = get_code_type(purchased_codes[0], vouchers)
    else:
        code_type = 'voucher_code'
    
    for vv in vouchers:
        if vv[code_type] not in purchased_codes:
            print "returning voucher... " + str(vv['id']) + " / " + str(vv[code_type])
            #tippr_client.return_voucher(vv['id'])

    logger.info("Closing Promotion ID %s" % str(pid))
    #response = tippr_client.close_promotion(pid)
    #logger.info("Promotion ID %s closed. Response is: %s" % (str(pid), str(response)))
    
def process_closed_promotion(tippr_client, g_client, promotion):
    pid = promotion['id']
    vouchers = tippr_client.find_vouchers(pid)
    
    try:
        codes = g_client.GetRedemptionCodesWithStatus(pid, 'REFUNDED')
        refunded = codes.get('offer', {}).get('codes')
        # if there are refunded vouchers at google...  
        if refunded:
            for voucher in vouchers:
                found = False
                for r in refunded:
                    if voucher['voucher_code'] == r['id'] or r['id'] == voucher['redemption_code']:
                        logger.info("PromotionID: %s - Voucher: %s - Redemption Code: %s == %s - Returned succesfully!" % (pid, voucher, voucher['voucher_code'], r['id']))
                        #tippr_client.return_voucher(voucher['id'])
                        found = True
            if not found:
                logger.info("PromotionID: %s - Voucher: %s NOT FOUND" % (pid, voucher['voucher_id']))
    except Exception, e:
        logging.exception(e)
    

def sync(tippr_client, g_client):
    conn = open_connection()
    cursor = conn.cursor()
    
    try:
        promotions = tippr_client.find_promotions()

        for promotion in promotions:
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
                    
                    if promotion_status in ['approved', 'closed']:
                        #check if we need to close the offer at TOM
                        if end_date < today and end_date >= yesterday:
                            process_expired_promotion(tippr_client, g_client, promotion)
                    
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
