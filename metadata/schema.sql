
drop table if exists google_offers CASCADE;

create table google_offers (
  tippr_offer_id varchar(100),
  status varchar(100),
  last_update date
);

