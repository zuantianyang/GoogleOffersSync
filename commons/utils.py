import logging
logger = logging.getLogger('googleoffers-sync')

def find_redemption_codes(g_client, pid, status):
    redemption_codes = g_client.GetRedemptionCodesWithStatus(pid, status)
    return redemption_codes.get('offer', {}).get('codes', [])

def get_code_type(codes, vouchers):
    """ Find out if this is a voucher_code or redemption_code """
    if codes:
        code = codes[0]
        for v in vouchers:
            if code in v['voucher_code']:
                return 'voucher_code'
            elif v['redemption_code']:
                return 'redemption_code'
        logger.info("Unable to find voucher code %s" % code['id'])
    else:
        return 'voucher_code'
 
