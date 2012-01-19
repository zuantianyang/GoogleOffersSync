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
            'tippr-api': {
                'handlers': ['console'],
                'level'   : 'DEBUG'
                }
        }
}

logging.config.dictConfig(LOGGING)
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

conn = open_connection()
cursor = conn.cursor()

today = date.today()

def register_offer(conn, cursor, promotion, g_status):
    data = {
            'tippr_offer_id': promotion['id'],
            'status'        : g_status,
            'last_update'   : today
            }
    insert(cursor, 'google_offers', data.keys(), data)

def update_redemption_data(redemtion_data, g_status, codes):
    #if g_status in ['active']: #TODO
    for g_status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
        size = len(codes.get('offer', {}).get('codes', []))
        redemtion_data[g_status] = redemtion_data.get(g_status, 0) + size
    return redemtion_data

try:
    tippr_client = TipprAPIClient()
    g_client = GoogleOffers('8793954', TOKEN_FILE, SECRETS_FILE)
    promotions = tippr_client.find_promotions()

#    redemtion_data = dict()
#    for i, promotion in enumerate(promotions):
#
#        if promotion['status'] in ['approved', 'active', 'closed']:
#            try:
#                pid = promotion['id']
#                g_status = g_client.GetOfferStatus(pid)
#
#                register_offer(conn, cursor, promotion, g_status)
#
#                redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, g_status)
#
#                redemtion_data = update_redemption_data(redemtion_data, g_status, redemption_codes)   

###                end_date = datetime.datetime.strptime(promotion['end_date'], "%Y-%m-%d").date()
###                if end_date < today and 'error' not in redemption_codes: #comprobacion 
###                    for voucher in redemption_codes.get('offer', {}).get('codes', []):
###                        if voucher['status'] not in ['PURCHASED', 'REDEEMED', 'REFUNDED', 'REFUND_HOLD']:
###                            print "PromotionID = " + pid + " - Voucher: " + str(voucher)
###                            print tippr_client.return_voucher(voucher['id'])
###                    tippr_client.close_promotion(pid)

#                if i % 10:
#                    conn.commit()
#            except GoogleOffersError:
#                logging.exception("Error in google offers")
#
#    for g_status in ['CREATED', 'PURCHASED', 'REDEEMED', 'REFUND_HOLD', 'REFUNDED', 'CANCELLED']:
#        data = {
#                'size'       : redemtion_data.get(g_status, 0),
#                'status'     : g_status,
#                'last_update': today
#                }
#        insert(cursor, 'redemption_codes', data.keys(), data)
#        conn.commit()
        
except Exception, e:
    logging.exception("Error in google offers sync")
    
    
      
# TX - PROCESO DE CIERRE DE PROMOS
try:
    promotions = tippr_client.find_promotions()
    
    for i, promotion in enumerate(promotions):  
        

            
        end_date = datetime.datetime.strptime(promotion['end_date'], "%Y-%m-%d").date()
        pid = promotion['id']
        
        
        #ignoramos las promociones que no estan activas
        if promotion['status'] not in ['expired']:
            print "Ignoring promotion " + str(pid) + " status is " + promotion['status']
            continue
        
        if end_date < today: # si la promocion ha vencido...
            
            # leer todos los redemption codes de google que NO esten en  ['PURCHASED', 'REDEEMED', 'REFUNDED', 'REFUND_HOLD'] para esta promocion
            # si no encuentra la promocion en google offers, la ignoramos y pasamos a la siguiente
            try:
                redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, "CREATED")
            except Exception, e:    
                logging.exception(e)
                continue
            
            #traer todos los vouchers de la oferta
            vouchers = tippr_client.get_vouchers(pid)

            for r in redemption_codes.get('offer', {}).get('codes', []):         
                for x, voucher in enumerate(vouchers):
                    
                    # ignoramos los vouchers que ya han sido devueltos
                    if voucher['status'] == "returned":
                        continue
                    
                    #si el redemption_code del voucher coincide con el de google offers, lo devolvemos
                    if voucher['redemption_code'] == r['id']:
                        
                        print "PromotionID = " + pid + " - Voucher: " + str(voucher) + " - Redemption Code: " + str(r['id'])  
                        print tippr_client.return_voucher(voucher['id'])

                            
            # cuando estan todos devueltos, cerrar la promocion                           
            print tippr_client.close_promotion(pid)
        
        
        
        
        
except Exception, e:
    logging.exception("Error in google offers sync")        
        
        
        
        


conn.commit()
cursor.close()
conn.close()
