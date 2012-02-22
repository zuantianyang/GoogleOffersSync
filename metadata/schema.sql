/*
 Navicat Premium Data Transfer

 Source Server         : PostgreSQL @ tesla
 Source Server Type    : PostgreSQL
 Source Server Version : 90004
 Source Host           : localhost
 Source Database       : googleoffers
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 90004
 File Encoding         : utf-8

 Date: 01/23/2012 14:48:54 PM
*/

-- ----------------------------
--  Table structure for "advertisers"
-- ----------------------------
DROP TABLE IF EXISTS "advertisers" CASCADE;
CREATE TABLE "advertisers" (
	id varchar(100) PRIMARY KEY,
    name varchar(100)
)
WITH (OIDS=FALSE);
ALTER TABLE "advertisers" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "categories"
-- ----------------------------
DROP TABLE IF EXISTS "categories" CASCADE;
CREATE TABLE "categories" (
	id varchar(100) PRIMARY KEY,
    name varchar(100),
    label varchar(100)
)
WITH (OIDS=FALSE);
ALTER TABLE "categories" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "promotions"
-- ----------------------------
DROP TABLE IF EXISTS "promotions" CASCADE;
CREATE TABLE "promotions" (
  	id varchar(100) PRIMARY KEY,
    --first_observed, 
    marketplace_status varchar(50), 
    headline varchar(200), 
    name varchar(100),
    start_date timestamp,
    end_date timestamp,
    category_id varchar(100) REFERENCES categories (id),
    advertiser_id varchar(100) REFERENCES advertisers (id)
)
WITH (OIDS=FALSE);
ALTER TABLE "promotions" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "markets"
-- ----------------------------
DROP TABLE IF EXISTS "markets" CASCADE;
CREATE TABLE "markets" (
	id varchar(100) PRIMARY KEY,
    name varchar(100)
)
WITH (OIDS=FALSE);
ALTER TABLE "markets" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "promotion_market"
-- ----------------------------
CREATE SEQUENCE id_promotion_market_seq INCREMENT 1 START 600 MAXVALUE 9223372036854775807 MINVALUE 1 CACHE 1;
ALTER TABLE id_promotion_market_seq OWNER TO postgres;

DROP TABLE IF EXISTS "promotion_market";
CREATE TABLE "promotion_market" (
    id int8 DEFAULT nextval('id_promotion_market_seq'::regclass) PRIMARY KEY,
	"promotion_id" varchar(100) REFERENCES promotions (id),
	"market_id" varchar(100) REFERENCES markets (id)
)
WITH (OIDS=FALSE);
ALTER TABLE "promotion_market" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "promotion_status_history"
-- ----------------------------
DROP TABLE IF EXISTS "promotion_status_history";
CREATE TABLE "promotion_status_history" (
	"promotion_id" varchar(100) REFERENCES promotions (id),
	"status" varchar(100),
	"last" boolean,
	"last_update" timestamp(6) NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "promotion_status_history" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "redemption_codes"
-- ----------------------------
DROP TABLE IF EXISTS "redemption_codes";
CREATE TABLE "redemption_codes" (
	"promotion_id" varchar(100) REFERENCES promotions (id),
	"size" int4,
	"status" varchar(20),
	"last" boolean,
	"last_update" timestamp(6) NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "redemption_codes" OWNER TO "postgres";
