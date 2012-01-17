drop table if exists google_offers CASCADE;

create table google_offers (
  tippr_offer_id varchar(100),
  status varchar(100),
  last_update date
);

drop table if exists redemption_codes CASCADE;

create table redemption_codes (
  size int,
  status varchar(20),
  last_update date
);

