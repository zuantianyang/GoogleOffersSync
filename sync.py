import logging
import sys
import commons.dictconfig
import ConfigParser

################
#Configuration:
import logging.config


LOGGING = {
        'version': 1.0,
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler'
            },
            'file': {
               'level': 'DEBUG',      
               'class' : 'logging.handlers.RotatingFileHandler',
               'filename': 'gofferssync_log.log'
            }         
        },                                                                                                                     
        'loggers': {
            'googleoffers-sync': {
                'handlers': ['console', 'file'],
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

#TOKEN_FILE ='/usr/local/GoogleOffersSync/metadata/tokens.dat'
#SECRETS_FILE = '/usr/local/GoogleOffersSync/metadata/client_secrets.json'
################

import datetime
import calendar
from datetime import date, time, timedelta
from tipprapi.tipprapi import TipprAPIClient
from googleoffers.client import GoogleOffers
from commons import configuration
from commons.persistence import dinsert, register_named_entity
import pytz

logger = logging.getLogger('googleoffers-sync')


class EST(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-5)

    def dst(self, dt):
        return datetime.timedelta(0)

#today = date.today()
today = datetime.datetime.now(EST())
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
    
    logger.info("======================================")
    logger.info("UPDATING REDEMPTION DATA FOR %s" % pid)
    
    for status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
        try:
            redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, status)                        
            size = len(redemption_codes.get('offer', {}).get('codes', []))
                    
            logger.info("GetRedemptionCodesWithStatus found -> %s / %s / %s" % (pid, status, size))
            data = {
                    'promotion_id': pid,
                    'size'        : size,
                    'status'      : status,
                    'last'        : True,
                    'last_update' : datetime.datetime.now()
                    }
            cursor.execute('update redemption_codes set last=false where promotion_id = %s and status=%s', [pid, status])
            dinsert(cursor, 'redemption_codes', data)
                
        except Exception, e:
            logging.exception("UpdatingRedemptionData Exception -> %s " % str(e))
            continue
    
    conn.commit()
        
def get_vouchers_from_tom(tippr_client, pid, status=None):    
    vouchers = tippr_client.find_vouchers2(pid)

    if status is None:
        return vouchers
    else:
        v = []
        for voucher in vouchers:
            if voucher['status'] == status:
                v.append(voucher)
        return v
        
        
        
        
def process_expired_promotion(tippr_client, g_client, promotion):
    pid = promotion['id']
    
    #retrieve all offer's vouchers from TOM
    vouchers_at_tom = get_vouchers_from_tom(tippr_client, pid)
    
        
    purchased_codes = []
    try:
        codes = g_client.GetRedemptionCodesWithStatus(pid, 'PURCHASED')
        purchased_codes = [c['id'] for c in codes.get('offer').get('codes', [])]
    except:
        pass    

       
    logger.info("*** CLOSING PROMOTION (START) ***")
    logger.info("---------------------------------")
    
    
    returned_count = 0
    purchased_count = 0
        
    for v in vouchers_at_tom:
        if v['voucher_code'] not in purchased_codes:   
            if v['redemption_code'] not in purchased_codes:
                response = tippr_client.return_voucher(v['id'])
                        
                if 'errors' in response:
                    logger.critical("Error returning voucher: Promotion ID %s, voucher %s could no be returned. (status is %s)" % (pid, str(v['id']), v['status'])) 
                else:
                    logger.info("Voucher %s (status: %s) returned to TOM... Response is %s" % (str(v['id']), v['status'], str(response)))
                    returned_count +=1
            else:
                logger.info("Voucher %s / %s has been purchased at Google. Leaving its status as assigned" % (str(v['id']), v['redemption_code']))
                purchased_count += 1
        else:
            logger.info("Voucher %s / %s has been purchased at Google. Leaving its status as assigned" % (str(v['id']), v['voucher_code']))
            purchased_count += 1   
     
     
    #check if everything is OK (purchased at TOM == purchased at Google) 
    purchased_at_tom = get_vouchers_from_tom(tippr_client, pid, "assigned")
    
    if len(purchased_at_tom) == len(purchased_codes):
        logger.info("%s Vouchers were successfully returned" % str(returned_count))
        logger.info("Closing Promotion ID %s" % str(pid))
        response = tippr_client.close_promotion(pid)
        logger.info("Promotion ID %s closed. Response is: %s" % (str(pid), str(response)))
    else:    
        logger.critical("Error! Promotion ID %s. Total Purchased at TOM %s. Total Purchased at Google %s. The promotion was NOT closed." % (pid, str(len(purchased_at_tom)), str(len(purchased_codes))))

    logger.info("*** CLOSING PROMOTION (END) ***")
    logger.info("-------------------------------")    
    

def sync(tippr_client, g_client):
    conn = configuration.open_connection()
    cursor = conn.cursor()
    
    try:
        promotions = tippr_client.find_promotions()
        logger.info("Total Promotions: %s. Run time: %s" % (len(promotions), str(datetime.datetime.now())))
        
        for promotion in promotions:
            pid = promotion['id']
            g_status = None    
            
            promotion_status = promotion['status']
            publisher = promotion['publisher']['name']
            #ignore already closed promotions
            if promotion_status == 'closed':
                continue
            
            if publisher != 'Google':
                continue
                      
            EST_tz = pytz.timezone('US/Eastern')
            
            end_offer_date = datetime.datetime.strptime(promotion['end_date'], "%Y-%m-%d").date()
            end_date = datetime.datetime(end_offer_date.year, end_offer_date.month, end_offer_date.day, 23, 59, 59)
            end_date = EST_tz.localize(end_date)
                      
            logger.info('Processing promotion id: %s, %s, status is %s, expires on %s ' % (pid, promotion['name'], promotion_status, end_date))
         

            register_promotion(conn, cursor, promotion)
            
            try:
                         
                                    
                if end_date < today and end_date >= yesterday:
                    process_expired_promotion(tippr_client, g_client, promotion)
                                           
                g_status = g_client.GetOfferStatus(pid)
                if g_status == "-1":
                    g_status = "NOT_EXISTS" 
                
                register_promotion_history(conn, cursor, promotion, g_status)
                update_redemption_data(conn, cursor, g_client, pid)
                                       
            except Exception, e:
                logging.exception("Error in google offers" + str(e))
                

                
    except Exception, e:
        logging.exception("Error in google offers sync" + str(e))

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("*** END ***")

def main():
    cfg = ConfigParser.ConfigParser()
    cfg.readfp(open(configuration.CONFIG_FILE))
    tippr_client = TipprAPIClient(cfg.get('Marketplace','url'),cfg.get('Marketplace','apikey'))
    g_client = GoogleOffers(cfg.get('Google','partner_id'), cfg.get('Google','token_file'), cfg.get('Google', 'secrets_file'))
    sync(tippr_client, g_client)
    
   
if __name__ == "__main__":
    configuration.CONFIG_FILE = sys.argv[1]
    main()
